import { Loader2, Trash2 } from 'lucide-react';

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

interface AssetVariantDeleteDialogProps {
  title: string;
  open: boolean;
  deleting: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
}

function AssetVariantDeleteDialog({
  title,
  open,
  deleting,
  onOpenChange,
  onConfirm,
}: AssetVariantDeleteDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>将延展版本“{title}”移入回收站？</AlertDialogTitle>
          <AlertDialogDescription>
            只会移除这个版本，正式主图、同组卖点关系和其他尺寸不会受到影响；需要时可从回收站恢复。
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={deleting}>取消</AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            disabled={deleting}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {deleting ? (
              <><Loader2 className="mr-1.5 size-4 animate-spin" />处理中...</>
            ) : (
              <><Trash2 className="mr-1.5 size-4" />移入回收站</>
            )}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

export default AssetVariantDeleteDialog;
