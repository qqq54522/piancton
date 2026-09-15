import { useState } from 'react';

import { getApiError } from '@client/src/api/client';
import { Button } from '@client/src/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@client/src/components/ui/dialog';
import { useAuth } from '@client/src/lib/auth';
import AvatarChoices from './AvatarChoices';
import type { AvatarPresetId } from './AccountAvatar';

export default function AccountAvatarDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const { user, uploadAvatar, selectAvatarPreset } = useAuth();
  const [presetId, setPresetId] = useState<AvatarPresetId>((user?.avatarPresetId as AvatarPresetId) || 'blue');
  const [file, setFile] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const save = async () => {
    setSaving(true); setError('');
    try {
      if (file) await uploadAvatar(file);
      else await selectAvatarPreset(presetId);
      setFile(null);
      onOpenChange(false);
    } catch (requestError) {
      setError(getApiError(requestError).message);
    } finally { setSaving(false); }
  };

  return <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent className="max-w-md rounded-2xl">
      <DialogHeader><DialogTitle>更换账号头像</DialogTitle><DialogDescription>头像只属于你的账号，不会出现在素材图库里。</DialogDescription></DialogHeader>
      <AvatarChoices presetId={presetId} onPresetChange={setPresetId} file={file} onFileChange={setFile} disabled={saving} />
      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
      <DialogFooter><Button disabled={saving} onClick={() => void save()}>{saving ? '保存中…' : '保存头像'}</Button></DialogFooter>
    </DialogContent>
  </Dialog>;
}
