import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

@Injectable()
export class LockService {
  private readonly logger = new Logger(LockService.name);
  private lockStatus: 'OPEN' | 'CLOSED' = 'CLOSED';
  private gpioPin: number;
  private isSimulated: boolean;

  constructor(private configService: ConfigService) {
    this.gpioPin = this.configService.get<number>('GPIO_RELAY_PIN') || 17;
    this.isSimulated = this.configService.get<boolean>('GPIO_SIMULATED') !== false;
    
    if (this.isSimulated) {
      this.logger.log(`GPIO operations simulated (GPIO_PIN: ${this.gpioPin})`);
    } else {
      this.logger.log(`GPIO operations enabled (GPIO_PIN: ${this.gpioPin})`);
    }
  }

  /**
   * Open the door/lock by triggering the relay
   */
  async openDoor(): Promise<{ status: string; message: string; pin: number }> {
    try {
      this.logger.log('Opening door...');
      
      if (this.isSimulated) {
        this.logger.debug(`[SIMULATED] Triggering GPIO ${this.gpioPin} - Door OPEN`);
      } else {
        // Real GPIO implementation would go here
        // Example with onoff:
        // const Gpio = require('onoff').Gpio;
        // const relay = new Gpio(this.gpioPin, 'out');
        // await relay.write(1);
        // setTimeout(() => relay.write(0), 5000); // Auto-close after 5 seconds
        // relay.unexport();
      }
      
      this.lockStatus = 'OPEN';
      
      return {
        status: 'SUCCESS',
        message: 'Door opened successfully',
        pin: this.gpioPin,
      };
    } catch (error) {
      this.logger.error(`Failed to open door: ${error.message}`);
      throw error;
    }
  }

  /**
   * Close the door/lock
   */
  async closeDoor(): Promise<{ status: string; message: string; pin: number }> {
    try {
      this.logger.log('Closing door...');
      
      if (this.isSimulated) {
        this.logger.debug(`[SIMULATED] Resetting GPIO ${this.gpioPin} - Door CLOSED`);
      } else {
        // Real GPIO implementation would go here
      }
      
      this.lockStatus = 'CLOSED';
      
      return {
        status: 'SUCCESS',
        message: 'Door closed successfully',
        pin: this.gpioPin,
      };
    } catch (error) {
      this.logger.error(`Failed to close door: ${error.message}`);
      throw error;
    }
  }

  /**
   * Get current lock status
   */
  async getStatus(): Promise<{
    status: 'OPEN' | 'CLOSED';
    pin: number;
    simulated: boolean;
  }> {
    return {
      status: this.lockStatus,
      pin: this.gpioPin,
      simulated: this.isSimulated,
    };
  }

  /**
   * Toggle lock state
   */
  async toggle(): Promise<{ previousStatus: string; currentStatus: string; pin: number }> {
    const previousStatus = this.lockStatus;
    
    if (this.lockStatus === 'CLOSED') {
      await this.openDoor();
    } else {
      await this.closeDoor();
    }
    
    return {
      previousStatus,
      currentStatus: this.lockStatus,
      pin: this.gpioPin,
    };
  }
}