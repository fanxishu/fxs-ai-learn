import React, { useEffect, useRef } from 'react';
import { useDidShow, useDidHide } from '@tarojs/taro';
import { useUserStore } from '@/store/user';
import './app.scss';

function App(props) {
  const wxLoginFlow = useUserStore(s => s.wxLoginFlow)
  const refreshProfile = useUserStore(s => s.refreshProfile)
  const isLoggedIn = useUserStore(s => s.isLoggedIn)
  const hasAutoLogin = useRef(false)

  useEffect(() => {
    if (!hasAutoLogin.current) {
      hasAutoLogin.current = true
      wxLoginFlow().catch(err => console.error('[App] auto-login error', err))
    }
  }, [wxLoginFlow])

  useDidShow(() => {
    if (isLoggedIn) {
      refreshProfile().catch(err => console.error('[App] didShow refreshProfile error', err))
    } else if (!hasAutoLogin.current) {
      hasAutoLogin.current = true
      wxLoginFlow().catch(err => console.error('[App] didShow login error', err))
    }
  });

  useDidHide(() => {});

  return props.children;
}

export default App;
