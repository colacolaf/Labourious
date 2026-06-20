"""Backtest UI API — trigger, poll, history."""
import uuid
import asyncio
import json
import sys
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select

from backend.database.db import get_db_session
from backend.database.models import BacktestResult
from backend.config import settings
from backend.utils.logger import setup_logger

router = APIRouter(prefix="/api/backtest", tags=["backtest"])
logger = setup_logger("backtest_ui")


class BacktestRunRequest(BaseModel):
    agent_id: int
    start_date: str          # "YYYY-MM-DD"
    end_date: str            # "YYYY-MM-DD"
    mode: str = "basic"      # "basic" | "walk_forward"
    symbol: Optional[str] = None  # override; defaults to agent's symbol


@router.post("/run")
async def run_backtest(req: BacktestRunRequest):
    """Create a BacktestResult row (status=running), kick off subprocess, return run_id."""
    run_id = str(uuid.uuid4())

    with get_db_session(settings.DATABASE_URL) as session:
        result = BacktestResult(
            id=run_id,
            agent_id=req.agent_id,
            run_at=datetime.utcnow(),
            start_date=req.start_date,
            end_date=req.end_date,
            mode=req.mode,
            status="running",
        )
        session.add(result)
        session.commit()

    # Run backtest in background — don't await, returns immediately
    asyncio.create_task(_run_backtest_task(run_id, req))
    return {"run_id": run_id}


async def _run_backtest_task(run_id: str, req: BacktestRunRequest) -> None:
    """Background task — runs CLI, writes result to DB."""
    try:
        cmd = [
            sys.executable, "-m", "backend.scripts.backtest",
            "--start", req.start_date,
            "--end", req.end_date,
            "--mode", req.mode,
        ]
        if req.symbol:
            cmd += ["--symbol", req.symbol]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

        if proc.returncode == 0:
            result_data = json.loads(stdout.decode())
            status = "done"
        else:
            result_data = {"error": stderr.decode()[:500]}
            status = "failed"

    except asyncio.TimeoutError:
        result_data = {"error": "backtest timed out after 120s"}
        status = "failed"
    except Exception as e:
        result_data = {"error": str(e)}
        status = "failed"

    with get_db_session(settings.DATABASE_URL) as session:
        row = session.execute(
            select(BacktestResult).where(BacktestResult.id == run_id)
        ).scalar_one_or_none()
        if row:
            row.status = status
            row.result_json = result_data
            session.commit()


@router.get("/history")
async def get_history(agent_id: Optional[int] = Query(default=None)):
    """List past backtest runs, newest first."""
    with get_db_session(settings.DATABASE_URL) as session:
        q = select(BacktestResult).order_by(BacktestResult.run_at.desc()).limit(50)
        if agent_id is not None:
            q = q.where(BacktestResult.agent_id == agent_id)
        results = session.execute(q).scalars().all()

        # Serialize within session to avoid detached instance errors
        return [
            {
                "id": r.id,
                "agent_id": r.agent_id,
                "run_at": r.run_at.isoformat(),
                "start_date": r.start_date,
                "end_date": r.end_date,
                "mode": r.mode,
                "status": r.status,
            }
            for r in results
        ]


@router.get("/{run_id}")
async def get_run(run_id: str):
    """Poll a single backtest run — returns status + result_json when done."""
    with get_db_session(settings.DATABASE_URL) as session:
        row = session.execute(
            select(BacktestResult).where(BacktestResult.id == run_id)
        ).scalar_one_or_none()

        if not row:
            raise HTTPException(status_code=404, detail=f"Backtest run {run_id} not found")

        # Serialize within session to avoid detached instance errors
        return {
            "id": row.id,
            "agent_id": row.agent_id,
            "status": row.status,
            "mode": row.mode,
            "start_date": row.start_date,
            "end_date": row.end_date,
            "run_at": row.run_at.isoformat(),
            "result_json": row.result_json,
        }
