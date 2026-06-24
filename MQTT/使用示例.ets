/**
 * 使用示例 — 在 APP 主页面中集成 MQTT
 * 替换原来 BLE 扫描/连接相关代码
 */

import { mqttManager, PetStatus } from './MqttManager';

// ==================== 1. 初始化连接（在 aboutToAppear 中调用） ====================

aboutToAppear(): void {
  mqttManager.connect()
    .then(() => {
      console.log('MQTT 连接成功');
    })
    .catch((err) => {
      console.error('MQTT 连接失败:', err);
      // 可尝试重连或提示用户检查网络
    });

  // 注册状态回调：收到 pet/status 时自动更新 UI
  mqttManager.onStatusUpdate((status: PetStatus) => {
    this.temperature = status.temp;   // 绑定到 UI 变量
    this.humidity = status.humi;
    this.currentMode = status.mode;
  });
}

// ==================== 2. 发送喂食指令 ====================

// 少量喂食按钮
onFeedSmall(): void {
  mqttManager.sendFeedCommand(30);
}

// 中量喂食按钮
onFeedMedium(): void {
  mqttManager.sendFeedCommand(60);
}

// 大量喂食按钮
onFeedLarge(): void {
  mqttManager.sendFeedCommand(90);
}

// ==================== 3. 断开连接（在 aboutToDisappear 中调用） ====================

aboutToDisappear(): void {
  mqttManager.disconnect();
}
