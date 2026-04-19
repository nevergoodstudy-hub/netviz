import { create } from 'zustand'

export interface ToastItem {
  id: string
  title: string
  description?: string
  type?: 'default' | 'success' | 'error' | 'warning'
}

interface ToastStore {
  toasts: ToastItem[]
  addToast: (toast: Omit<ToastItem, 'id'>) => void
  removeToast: (id: string) => void
}

export const useToast = create<ToastStore>((set) => ({
  toasts: [],
  addToast: (toast) =>
    set((state) => ({
      toasts: [...state.toasts, { ...toast, id: Math.random().toString(36).slice(2) }],
    })),
  removeToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((toast) => toast.id !== id),
    })),
}))

export function toast(options: Omit<ToastItem, 'id'>) {
  useToast.getState().addToast(options)
}
