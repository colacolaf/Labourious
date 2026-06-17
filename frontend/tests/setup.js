// Vitest/Jest setup file for frontend tests
// Phase 1: minimal setup — no component tests yet

global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};
