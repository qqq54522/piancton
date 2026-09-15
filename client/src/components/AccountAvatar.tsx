import { Avatar, AvatarFallback, AvatarImage } from '@client/src/components/ui/avatar';
import type { User } from '@client/src/types/api';

export const AVATAR_PRESETS = [
  { id: 'blue', label: '海蓝', colors: 'from-sky-400 to-blue-700' },
  { id: 'mint', label: '青绿', colors: 'from-emerald-300 to-teal-700' },
  { id: 'coral', label: '暖橙', colors: 'from-orange-300 to-rose-600' },
  { id: 'violet', label: '紫罗兰', colors: 'from-violet-300 to-indigo-700' },
  { id: 'gold', label: '金黄', colors: 'from-amber-300 to-orange-600' },
  { id: 'slate', label: '深灰', colors: 'from-slate-400 to-slate-800' },
] as const;

export type AvatarPresetId = typeof AVATAR_PRESETS[number]['id'];

function presetFor(user?: Pick<User, 'username' | 'avatarPresetId'> | null) {
  const selected = AVATAR_PRESETS.find(({ id }) => id === user?.avatarPresetId);
  if (selected) return selected;
  const name = user?.username || '';
  const hash = Array.from(name).reduce((sum, character) => sum + character.charCodeAt(0), 0);
  return AVATAR_PRESETS[hash % AVATAR_PRESETS.length];
}

export default function AccountAvatar({ user, className = 'size-8' }: { user?: User | null; className?: string }) {
  const preset = presetFor(user);
  const initial = user?.username?.trim().slice(0, 1).toUpperCase() || '我';
  const imageUrl = user?.hasCustomAvatar
    ? `/api/auth/avatar?v=${encodeURIComponent(user.avatarUpdatedAt || '')}`
    : undefined;
  return (
    <Avatar className={`border border-white/70 ${className}`}>
      {imageUrl && <AvatarImage src={imageUrl} alt={`${user?.username}的头像`} className="object-cover" />}
      <AvatarFallback className={`bg-gradient-to-br ${preset.colors} text-sm font-bold text-white`}>
        {initial}
      </AvatarFallback>
    </Avatar>
  );
}

export function PresetAvatar({ id, initial = '我' }: { id: AvatarPresetId; initial?: string }) {
  const preset = AVATAR_PRESETS.find((item) => item.id === id)!;
  return <span className={`flex size-11 items-center justify-center rounded-full bg-gradient-to-br ${preset.colors} text-lg font-bold text-white`}>{initial}</span>;
}
