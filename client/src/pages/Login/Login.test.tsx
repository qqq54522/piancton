// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import Login from './Login';

const mocks = vi.hoisted(() => ({ register: vi.fn(), login: vi.fn() }));
vi.mock('@client/src/api/auth', () => ({ register: mocks.register }));
vi.mock('@client/src/lib/auth', () => ({ useAuth: () => ({ user: null, login: mocks.login }) }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

function openRegistration() {
  render(<MemoryRouter><Login /></MemoryRouter>);
  fireEvent.click(screen.getByRole('button', { name: '还没有账号？注册账号' }));
  fireEvent.change(screen.getByLabelText('账号'), { target: { value: 'new-user' } });
  fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'new-password' } });
}

it('checks confirmation before sending registration', () => {
  openRegistration();
  fireEvent.change(screen.getByLabelText('确认密码'), { target: { value: 'different' } });
  fireEvent.click(screen.getByRole('button', { name: '注册账号' }));
  expect(screen.getByRole('alert').textContent).toContain('两次输入的密码不一致');
  expect(mocks.register).not.toHaveBeenCalled();
});

it('returns to login after registration and preserves the account', async () => {
  mocks.register.mockResolvedValue({ username: 'new-user' });
  openRegistration();
  fireEvent.change(screen.getByLabelText('确认密码'), { target: { value: 'new-password' } });
  fireEvent.click(screen.getByRole('button', { name: '注册账号' }));
  await waitFor(() => expect(screen.getByRole('status').textContent).toContain('注册成功'));
  expect(mocks.register).toHaveBeenCalledWith('new-user', 'new-password', 'new-password');
  expect((screen.getByLabelText('账号') as HTMLInputElement).value).toBe('new-user');
  expect((screen.getByLabelText('密码') as HTMLInputElement).value).toBe('');
  fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'new-password' } });
  fireEvent.click(screen.getByRole('button', { name: '登录' }));
  await waitFor(() => expect(mocks.login).toHaveBeenCalledWith('new-user', 'new-password'));
});

it('keeps the form available after a failed request', async () => {
  mocks.register.mockRejectedValue(new Error('offline'));
  openRegistration();
  fireEvent.change(screen.getByLabelText('确认密码'), { target: { value: 'new-password' } });
  fireEvent.click(screen.getByRole('button', { name: '注册账号' }));
  await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('网络请求失败'));
  expect((screen.getByRole('button', { name: '注册账号' }) as HTMLButtonElement).disabled).toBe(false);
});
