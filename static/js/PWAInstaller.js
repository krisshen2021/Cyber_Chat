class PWAInstaller {
    constructor(buttonElement, cssConfig = {}) {
      this.buttonElement = buttonElement;
      this.cssConfig = cssConfig;
      this.deferredPrompt = null;
  
      // 應用CSS配置
      this.applyCSSConfig();
      // 檢查應用程序是否已經安裝
      this.checkAppInstalled();
      // 監聽 beforeinstallprompt 事件
      window.addEventListener('beforeinstallprompt', (e) => this.handleInstallPrompt(e));
  
      // 添加點擊事件監聽器
      this.buttonElement.addEventListener('click', () => this.installApp());
    }

    async checkAppInstalled() {
      console.log('檢查應用程序安裝狀態');
      if ('getInstalledRelatedApps' in navigator) {
        console.log('瀏覽器支持 getInstalledRelatedApps');
        try {
          const relatedApps = await navigator.getInstalledRelatedApps();
          console.log('相關應用程序:', relatedApps);
          if (relatedApps.length > 0) {
            // 應用程序已經安裝，隱藏按鈕
            this.buttonElement.style.display = 'none';
          } else {
            // 應用程序未安裝，顯示按鈕
            this.buttonElement.style.display = 'flex';
          }
        } catch (error) {
          console.error('檢查應用程序安裝狀態時出錯:', error);
        }
      } else {
        // 如果瀏覽器不支持 getInstalledRelatedApps，顯示按鈕
        console.log('瀏覽器不支持 getInstalledRelatedApps');
        this.buttonElement.style.display = 'flex';
      }
      if (window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true || document.referrer.includes('android-app://')) {
        console.log('應用程序已經以獨立模式運行');
        this.buttonElement.style.display = 'none';
      }
    }
  
  
    handleInstallPrompt(e) {
      // 防止瀏覽器顯示默認的安裝提示
      e.preventDefault();
      // 保存事件以便稍後觸發
      this.deferredPrompt = e;
      if (!this.deferredPrompt) {
        this.buttonElement.style.display = 'none';
      }
    }
  
    installApp() {
      // 檢查是否已經保存了安裝提示事件
      if (this.deferredPrompt) {
        // 觸發安裝提示
        this.deferredPrompt.prompt();
        // 等待用戶選擇
        this.deferredPrompt.userChoice.then((choiceResult) => {
          if (choiceResult.outcome === 'accepted') {
            console.log('用戶接受了安裝提示');
            // 隱藏安裝按鈕
            this.buttonElement.style.display = 'none';
          } else {
            console.log('用戶取消了安裝提示');
          }
          // 清除保存的事件
          this.deferredPrompt = null;
          
        });
      }
    }
  
    applyCSSConfig() {
      // 應用CSS配置
      for (const [key, value] of Object.entries(this.cssConfig)) {
        this.buttonElement.style[key] = value;
      }
    }
  }
  
  // 導出類
  export default PWAInstaller;