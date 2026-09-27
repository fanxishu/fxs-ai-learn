import React, { useEffect, useRef } from 'react';
import { useDidShow, useDidHide } from '@tarojs/taro';
import { useUserStore } from '@/store/user';
import './app.scss';

function App(props) {
  const wxLoginFlow = useUserStore(s => s.wxLoginFlow)
  const refreshProfile = useUserStore(s => s.refreshProfile)
  const isLoggedIn = useUserStore(s => s.isLoggedIn)
  const hasAutoLogin = useRef(false)
  const autoLoginRunning = useRef(false)

  useEffect(() => {
    if (!hasAutoLogin.current && !autoLoginRunning.current) {
      hasAutoLogin.current = true
      autoLoginRunning.current = true
      wxLoginFlow()
        .then(ok => console.info('[App] auto-login ok=', ok))
        .catch(err => console.error('[App] auto-login error', err))
        .finally(() => { autoLoginRunning.current = false })
    }
  }, [wxLoginFlow])

  useDidShow(() => {
    if (isLoggedIn) {
      refreshProfile().catch(err => console.error('[App] didShow refreshProfile error', err))
    } else if (!hasAutoLogin.current && !autoLoginRunning.current) {
      hasAutoLogin.current = true
      autoLoginRunning.current = true
      wxLoginFlow()
        .then(ok => console.info('[App] didShow-login ok=', ok))
        .catch(err => console.error('[App] didShow login error', err))
        .finally(() => { autoLoginRunning.current = false })
    }
  });

  useDidHide(() => {});

  return props.children;
}

export default App;
