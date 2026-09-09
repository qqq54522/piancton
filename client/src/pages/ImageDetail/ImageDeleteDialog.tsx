import { Loader2 } from 'lucide-react';

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@client/src/components/ui/alert-dialog';

interface ImageDeleteDialogProps {
  title: string;
  open: boolean;
  deleting: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
}

const ImageDeleteDialog = ({
  title,
  open,
  deleting,
  onOpenChange,
  onConfirm,
}: ImageDeleteDialogProps) => (
  <AlertDialog open={open} onOpenChange={onOpenChange}>
    <AlertDialogContent>
      <AlertDialogHeader>
        <AlertDialogTitle>确认删除图片「{title}」？</AlertDialogTitle>
        <AlertDialogDescription>
          图片会移入回收站并立即释放当前名称；素材组卖点关系不会被删除，需要时可以恢复。
        </AlertDialogDescription>
      </AlertDialogHeader>
      <AlertDialogFooter>
        <AlertDialogCancel>取消</AlertDialogCancel>
        <AlertDialogAction
          onClick={onConfirm}
          disabled={deleting}
          className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
        >
          {deleting ? (
            <><Loader2 className="mr-1.5 size-4 animate-spin" />删除中...</>
          ) : (
            '确认删除'
          )}
        </AlertDialogAction>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
);

export default ImageDeleteDialog;
