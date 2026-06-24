/**
 * MqttManager.ets — 宠物喂食系统 MQTT 通信模块
 * 替代原来的 NearLinkManager / BLE 代码
 * 依赖: 需要引入 MQTT 库 (如 paho-mqtt 或 @ohos/netmanager)
 */

import mqtt from '@ohos/mqttclient';  // 根据实际引入的 MQTT 库调整
// import { socket } from '@ohos.net.socket';  // 备选：原生 Socket 实现

// ==================== 连接参数（硬件队友提供） ====================
const MQTT_BROKER = '10.81.65.37';
const MQTT_PORT = 1883;
const MQTT_USERNAME = 'admin';
const MQTT_PASSWORD = 'pyz20040306';
const MQTT_CLIENT_ID = 'pet_app_' + Math.random().toString(36).substring(2, 10);

// Topic 定义
const TOPIC_STATUS = 'pet/status';     // 订阅：硬件 → App
const TOPIC_COMMAND = 'pet/command';   // 发布：App → 硬件

// ==================== 类型定义 ====================
export interface PetStatus {
  temp: number;   // 温度 ℃
  humi: number;   // 湿度 %
  mode: number;   // 模式 0=自动 1=手动
}

export interface FeedCommand {
  cmd: string;       // "feed"
  amount: number;    // 30=少量 60=中量 90=大量
}

// ==================== MQTT 管理器 ====================
export class MqttManager {
  private client: mqtt.MqttClient | null = null;
  private statusCallback: ((status: PetStatus) => void) | null = null;
  private connected: boolean = false;

  /**
   * 连接 MQTT Broker
   */
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        const options: mqtt.MqttConnectOptions = {
          host: MQTT_BROKER,
          port: MQTT_PORT,
          clientId: MQTT_CLIENT_ID,
          username: MQTT_USERNAME,
          password: MQTT_PASSWORD,
          keepAlive: 60,
          cleanSession: true,
        };

        this.client = mqtt.connect(options);

        this.client.on('connect', () => {
          console.log('[MQTT] Connected to', MQTT_BROKER);
          this.connected = true;
          this.subscribeToStatus();   // 连接后自动订阅
          resolve();
        });

        this.client.on('message', (topic: string, payload: ArrayBuffer) => {
          this.handleMessage(topic, payload);
        });

        this.client.on('error', (err: Error) => {
          console.error('[MQTT] Error:', err.message);
        });

        this.client.on('close', () => {
          console.log('[MQTT] Disconnected');
          this.connected = false;
        });

      } catch (err) {
        reject(new Error('MQTT 连接失败: ' + String(err)));
      }
    });
  }

  /**
   * 注册温湿度状态回调
   */
  onStatusUpdate(callback: (status: PetStatus) => void): void {
    this.statusCallback = callback;
  }

  /**
   * 发送喂食指令
   */
  sendFeedCommand(amount: number = 30): void {
    if (!this.connected || !this.client) {
      console.error('[MQTT] 未连接，无法发送指令');
      return;
    }

    const command: FeedCommand = {
      cmd: 'feed',
      amount: amount,  // 30/60/90
    };

    const payload = JSON.stringify(command);
    this.client.publish(TOPIC_COMMAND, payload);
    console.log('[MQTT] Published:', payload);
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    if (this.client) {
      this.client.close();
      this.client = null;
      this.connected = false;
    }
  }

  isConnected(): boolean {
    return this.connected;
  }

  // ==================== 内部方法 ====================

  /**
   * 订阅 pet/status 主题
   */
  private subscribeToStatus(): void {
    if (!this.client) return;
    this.client.subscribe(TOPIC_STATUS, (err: Error) => {
      if (err) {
        console.error('[MQTT] 订阅失败:', err.message);
      } else {
        console.log('[MQTT] Subscribed to', TOPIC_STATUS);
      }
    });
  }

  /**
   * 处理收到的消息
   */
  private handleMessage(topic: string, payload: ArrayBuffer): void {
    try {
      const raw = String.fromCharCode.apply(null, new Uint8Array(payload) as unknown as number[]);
      console.log('[MQTT] Received:', topic, raw);

      if (topic === TOPIC_STATUS) {
        const status: PetStatus = JSON.parse(raw);
        if (this.statusCallback) {
          this.statusCallback(status);
        }
      }
    } catch (err) {
      console.error('[MQTT] 消息解析失败:', err);
    }
  }
}

// ==================== 单例导出 ====================
export const mqttManager = new MqttManager();
