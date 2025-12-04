// Composable para notificaciones toast
import { ref } from 'vue'
import type { ToastNotification } from '~/types/admin'

const notifications = ref<ToastNotification[]>([])

export const useToast = () => {
  const showToast = (
    message: string,
    type: ToastNotification['type'] = 'info',
    duration: number = 3000
  ) => {
    const id = Date.now().toString()
    const notification: ToastNotification = {
      id,
      type,
      message,
      duration
    }

    notifications.value.push(notification)

    if (duration > 0) {
      setTimeout(() => {
        removeToast(id)
      }, duration)
    }

    return id
  }

  const removeToast = (id: string) => {
    const index = notifications.value.findIndex(n => n.id === id)
    if (index > -1) {
      notifications.value.splice(index, 1)
    }
  }

  const success = (message: string, duration?: number) => showToast(message, 'success', duration)
  const error = (message: string, duration?: number) => showToast(message, 'error', duration)
  const warning = (message: string, duration?: number) => showToast(message, 'warning', duration)
  const info = (message: string, duration?: number) => showToast(message, 'info', duration)

  return {
    notifications,
    showToast,
    removeToast,
    success,
    error,
    warning,
    info
  }
}

