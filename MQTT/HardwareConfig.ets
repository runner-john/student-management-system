/**
 * HardwareConfig.ets — 硬件通信配置
 * 替代原来的 BLE UUID / GATT 配置
 */

export const HardwareConfig = {
  // MQTT 参数
  mqtt: {
    broker: '10.81.65.37',
    port: 1883,
    username: 'admin',
    password: 'pyz20040306',
  },

  // Topic
  topic: {
    status: 'pet/status',     // 订阅：收温湿度
    command: 'pet/command',   // 发布：发喂食指令
  },

  // 喂食量映射
  feedAmount: {
    small: 30,     // 少量 — 舵机 30°
    medium: 60,    // 中量 — 舵机 60°
    large: 90,     // 大量 — 舵机 90°
  },
};
