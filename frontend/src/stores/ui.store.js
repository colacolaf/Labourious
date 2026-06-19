import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

export const useUIStore = create(
  devtools(
    (set) => ({
      currentRoom: 'lobby',
      inspectorOpen: false,
      notifications: [],
      pendingApproval: null,

      setCurrentRoom: (room) => set({ currentRoom: room }),
      openInspector: () => set({ inspectorOpen: true }),
      closeInspector: () => set({ inspectorOpen: false }),

      setPendingApproval: (approval) => set({ pendingApproval: approval }),
      clearPendingApproval: () => set({ pendingApproval: null }),

      addNotification: (notif) =>
        set((state) => ({
          notifications: [
            ...state.notifications,
            { id: Date.now(), ...notif },
          ],
        })),

      addToast: (notif) =>
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
