import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

export const useUIStore = create(
  devtools(
    (set) => ({
      currentRoom: 'lobby',
      inspectorOpen: false,
      notifications: [],

      setCurrentRoom: (room) => set({ currentRoom: room }),
      openInspector: () => set({ inspectorOpen: true }),
      closeInspector: () => set({ inspectorOpen: false }),

      addNotification: (notif) =>
        set((state) => ({
          notifications: [
            ...state.notifications,
            { id: Date.now(), ...notif },
          ],
        })),

      removeNotification: (id) =>
        set((state) => ({
          notifications: state.notifications.filter((n) => n.id !== id),
        })),

      clearNotifications: () => set({ notifications: [] }),
    }),
    { name: 'ui-store' }
  )
);
