import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

const useWizardStore = create(
  devtools(
    (set, get) => ({
      currentStep: 0,
      formData: {},
      isComplete: false,

      nextStep: () => set((s) => ({ currentStep: Math.min(s.currentStep + 1, 4) })),
      prevStep: () => set((s) => ({ currentStep: Math.max(s.currentStep - 1, 0) })),
      setFormData: (step, data) =>
        set((s) => ({ formData: { ...s.formData, [step]: { ...s.formData[step], ...data } } })),
      submitWizard: () => set({ isComplete: true }),
      reset: () => set({ currentStep: 0, formData: {}, isComplete: false }),
    }),
    { name: 'wizard-store' }
  )
);

export default useWizardStore;
