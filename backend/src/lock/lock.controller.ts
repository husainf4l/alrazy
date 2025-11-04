import {
  Controller,
  Post,
  Get,
  UseGuards,
  Param,
  Body,
  HttpCode,
} from '@nestjs/common';
import { ApiTags, ApiOperation, ApiBearerAuth } from '@nestjs/swagger';
import { LockService } from './lock.service';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';

@ApiTags('Lock Control')
@Controller('api/lock')
@UseGuards(JwtAuthGuard)
@ApiBearerAuth()
export class LockController {
  constructor(private readonly lockService: LockService) {}

  @Post('open')
  @HttpCode(200)
  @ApiOperation({ summary: 'Open the door (activate relay)' })
  async openDoor() {
    return this.lockService.openDoor();
  }

  @Post('close')
  @HttpCode(200)
  @ApiOperation({ summary: 'Close the door (deactivate relay)' })
  async closeDoor() {
    return this.lockService.closeDoor();
  }

  @Post('toggle')
  @HttpCode(200)
  @ApiOperation({ summary: 'Toggle lock state' })
  async toggle() {
    return this.lockService.toggle();
  }

  @Get('status')
  @ApiOperation({ summary: 'Get current lock status' })
  async getStatus() {
    return this.lockService.getStatus();
  }
}