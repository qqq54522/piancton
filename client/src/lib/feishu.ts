export interface FeishuAuthCodeResult {
  code: string;
}

interface FeishuSdk {
  ready: (callback: () => void) => void;
}

interface FeishuBridge {
  requestAuthCode: (options: {
    appId: string;
    success: (result: FeishuAuthCodeResult) => void;
    fail: (error: unknown) => void;
  }) => void;
}

declare global {
  interface Window {
    h5sdk?: FeishuSdk;
    tt?: FeishuBridge;
  }
}

let sdkPromise: Promise<boolean> | null = null;

export function isFeishuWebView(): boolean {
  return Boolean(window.tt) || /Lark|Feishu/i.test(window.navigator.userAgent);
}

function loadFeishuSdk(): Promise<boolean> {
  if (window.h5sdk && window.tt) return Promise.resolve(true);
  if (sdkPromise) return sdkPromise;
  const url = import.meta.env.VITE_FEISHU_H5_SDK_URL;
  if (!url) return Promise.resolve(false);
  sdkPromise = new Promise((resolve) => {
    const script = document.createElement('script');
    const timer = window.setTimeout(() => resolve(false), 4000);
    script.src = url;
    script.async = true;
    script.onload = () => {
      window.clearTimeout(timer);
      resolve(Boolean(window.h5sdk && window.tt));
    };
    script.onerror = () => {
      window.clearTimeout(timer);
      resolve(false);
    };
    document.head.appendChild(script);
  });
  return sdkPromise;
}

export async function requestFeishuAuthCode(): Promise<string | null> {
  const appId = import.meta.env.VITE_FEISHU_APP_ID;
  if (!appId || !(await loadFeishuSdk()) || !window.h5sdk || !window.tt) return null;
  return new Promise((resolve, reject) => {
    try {
      window.h5sdk?.ready(() => {
        window.tt?.requestAuthCode({
          appId,
          success: (result) => resolve(result.code || null),
          fail: () => reject(new Error('飞书授权未完成')),
        });
      });
    } catch (error) {
      reject(error);
    }
  });
}
