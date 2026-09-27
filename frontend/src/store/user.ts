import { create } from 'zustand'
import Taro from '@tarojs/taro'
import {
  API,
  clearAuthToken,
  setAuthToken as writeTokenStorage,
  getAuthToken as readTokenStorage,
  AUTH_TOKEN_KEY,
  toastError,
} from '@/services/api'
import type {
  UserProfile,
  ProfileStats,
  UserLoginResponse,
  UserProfileResponse,
} from '@/types/user'

export interface UserStoreState {
  token: string
  isLoggedIn: boolean
  user: UserProfile | null
  stats: ProfileStats | null
  loading: boolean

  setToken: (token: string) => void
  setUser: (u: UserProfile | null) => void
  setStats: (s: ProfileStats | null) => void
  setIsLoggedIn: (v: boolean) => void
  clearAuth: () => void

  wxLoginFlow: () => Promise<boolean>
  refreshProfile: () => Promise<boolean>
  updateNickname: (nickname: string) => Promise<boolean>
  updateAvatar: (filePath: string) => Promise<boolean>
}

export const useUserStore = create<UserStoreState>((set, get) => ({
  token: '',
  isLoggedIn: false,
  user: null,
  stats: null,
  loading: false,

  setToken: (t) => {
    set({ token: t })
    if (t) {
      writeTokenStorage(t)
      set({ isLoggedIn: true })
    } else {
      clearAuthToken()
      set({ isLoggedIn: false })
    }
    console.info('[UserStore] setToken token_len=', t?.length || 0, 'isLoggedIn=', !!t, 'storage=', (() => { try { return !!(Taro.getStorageSync(AUTH_TOKEN_KEY)) } catch { return false } })())
  },
  setUser: (u) => set({ user: u }),
  setStats: (s) => set({ stats: s }),
  setIsLoggedIn: (v) => set({ isLoggedIn: v }),
  clearAuth: () => {
    clearAuthToken()
    set({ token: '', isLoggedIn: false, user: null, stats: null })
  },

  wxLoginFlow: async () => {
    try {
      const exist = readTokenStorage()
      if (exist) {
        set({ token: exist, isLoggedIn: true })
        await get().refreshProfile()
        return true
      }
      set({ loading: true })
      const loginRes = await Taro.login()
      if (!loginRes || !loginRes.code) {
        console.warn('[UserStore] wx.login returned no code')
        return false
      }
      const res = await API.loginWx(loginRes.code)
      if (res.code !== 0 || !res.data) {
        console.warn('[UserStore] /user/login failed code=', res.code, 'msg=', res.message)
        return false
      }
      const payload = res.data as UserLoginResponse
      set({ token: payload.token, user: payload.user, isLoggedIn: true })
      writeTokenStorage(payload.token)
      set({ loading: false })
      console.info('[UserStore] wxLoginFlow SUCCESS token_len=', payload.token?.length || 0, 'payload_keys=', payload ? Object.keys(payload) : null, 'storage=', (() => { try { return !!(Taro.getStorageSync(AUTH_TOKEN_KEY)) } catch { return false } })())
      return true
    } catch (err) {
      console.error('[UserStore] wxLoginFlow error:', err)
      return false
    } finally {
      set({ loading: false })
    }
  },

  refreshProfile: async () => {
    if (!get().isLoggedIn && !readTokenStorage()) return false
    const requestToken = readTokenStorage()
    const previousAvatar = get().user?.avatar_url
    try {
      set({ loading: true })
      const res = await API.getProfile()
      if (res.code !== 0 || !res.data) {
        if (res.code === 2001 || res.code === 2002) get().clearAuth()
        return false
      }
      const data = res.data as UserProfileResponse
      if (readTokenStorage() !== requestToken) return false
      const currentUser = get().user
      // A refresh started before an upload must not overwrite the newly saved avatar.
      const nextUser = currentUser?.id === data.user.id && currentUser.avatar_url !== previousAvatar
        ? { ...data.user, avatar_url: currentUser.avatar_url }
        : data.user
      set({ user: nextUser, stats: data.stats })
      return true
    } catch (err) {
      console.error('[UserStore] refreshProfile error:', err)
      return false
    } finally {
      set({ loading: false })
    }
  },

  updateNickname: async (nickname: string) => {
    if (!nickname || !nickname.trim()) {
      toastError('昵称不能为空')
      return false
    }
    try {
      set({ loading: true })
      const res = await API.updateProfile({ nickname: nickname.trim() })
      if (res.code !== 0 || !res.data) {
        if (res.message) toastError(res.message)
        return false
      }
      const data = res.data as UserProfileResponse
      set({ user: data.user, stats: data.stats })
      Taro.showToast({ title: '修改成功', icon: 'success', duration: 1500 })
      return true
    } catch (err) {
      console.error('[UserStore] updateNickname error:', err)
      toastError('修改失败，请重试')
      return false
    } finally {
      set({ loading: false })
    }
  },

  updateAvatar: async (filePath: string) => {
    if (!filePath) return false
    const { token, user, isLoggedIn } = get()
    if (!isLoggedIn || !user) {
      toastError('请先登录后再修改头像')
      return false
    }
    try {
      set({ loading: true })
      const res = await API.uploadAvatar(filePath)
      if (get().token !== token || get().user?.id !== user.id) return false
      if (res.code !== 0 || !res.data) {
        toastError(res.message || '头像上传失败，请重试')
        return false
      }
      const avatarUrl = res.data.avatar_url
      set(state => ({
        user: state.user ? { ...state.user, avatar_url: avatarUrl } : null,
      }))
      return true
    } catch (err) {
      console.error('[UserStore] updateAvatar error:', err)
      toastError('头像上传失败，请重试')
      return false
    } finally {
      set({ loading: false })
    }
  },
}))
