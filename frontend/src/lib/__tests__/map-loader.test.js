// Note: only imports object-types.js (pure, Phaser-free) despite the filename — map-loader.js
// itself imports nothing Phaser-specific either, but this keeps the required test minimal.
import { computeOccupiedTiles } from '../object-types';

test('desk occupies tile', () => {
  const occupied = computeOccupiedTiles([{ id: '1', type: 'desk', col: 5, row: 5 }]);
  expect(occupied.has('5,5')).toBe(true);
});

test('meeting_table occupies its 2x2 footprint', () => {
  const occupied = computeOccupiedTiles([{ id: '1', type: 'meeting_table', col: 10, row: 8 }]);
  expect(occupied.size).toBe(4);
  expect(occupied.has('10,8')).toBe(true);
  expect(occupied.has('11,8')).toBe(true);
  expect(occupied.has('10,9')).toBe(true);
  expect(occupied.has('11,9')).toBe(true);
});
