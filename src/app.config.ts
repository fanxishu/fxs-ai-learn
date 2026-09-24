export default defineAppConfig({
  pages: [
    'pages/home/index',
    'pages/history/index',
    'pages/mine/index',
    'pages/loading/index',
    'pages/quiz/index',
    'pages/report/index',
    'pages/index/index'
  ],
  window: {
    backgroundTextStyle: 'light',
    navigationBarBackgroundColor: '#FFFFFF',
    navigationBarTitleText: '鱼皮 AI 闯关',
    navigationBarTextStyle: 'black',
    backgroundColor: '#F5F6F7'
  },
  tabBar: {
    color: '#86909C',
    selectedColor: '#165DFF',
    backgroundColor: '#FFFFFF',
    borderStyle: 'white',
    list: [
      {
        pagePath: 'pages/home/index',
        text: '首页',
        iconPath: 'assets/tabbar/home.svg',
        selectedIconPath: 'assets/tabbar/home-selected.svg'
      },
      {
        pagePath: 'pages/history/index',
        text: '历史',
        iconPath: 'assets/tabbar/history.svg',
        selectedIconPath: 'assets/tabbar/history-selected.svg'
      },
      {
        pagePath: 'pages/mine/index',
        text: '我的',
        iconPath: 'assets/tabbar/mine.svg',
        selectedIconPath: 'assets/tabbar/mine-selected.svg'
      }
    ]
  }
})

