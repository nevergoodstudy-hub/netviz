import * as Toast from '@radix-ui/react-toast'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useToast } from '@/components/ui/toast-store'

export function Toaster() {
  const { toasts, removeToast } = useToast()

  return (
    <Toast.Provider swipeDirection="right">
      {toasts.map((item) => (
        <Toast.Root
          key={item.id}
          className={cn(
            'bg-card border rounded-lg shadow-lg p-4 flex items-start gap-3',
            'data-[state=open]:animate-in data-[state=closed]:animate-out',
            'data-[swipe=end]:animate-out data-[state=closed]:fade-out-80',
            'data-[state=open]:slide-in-from-top-full data-[state=open]:sm:slide-in-from-bottom-full',
            item.type === 'error' && 'border-destructive',
            item.type === 'success' && 'border-green-500',
            item.type === 'warning' && 'border-yellow-500'
          )}
          onOpenChange={(open) => {
            if (!open) removeToast(item.id)
          }}
        >
          <div className="flex-1">
            <Toast.Title className="font-medium">{item.title}</Toast.Title>
            {item.description && (
              <Toast.Description className="text-sm text-muted-foreground mt-1">
                {item.description}
              </Toast.Description>
            )}
          </div>
          <Toast.Close className="text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
          </Toast.Close>
        </Toast.Root>
      ))}
      <Toast.Viewport className="fixed bottom-0 right-0 flex flex-col p-6 gap-2 w-96 max-w-full m-0 list-none z-50" />
    </Toast.Provider>
  )
}
