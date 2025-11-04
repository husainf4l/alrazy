import {
  Controller,
  Get,
  Post,
  Body,
  Param,
  Put,
  Delete,
  UseGuards,
} from '@nestjs/common';
import { ApiTags, ApiOperation, ApiBearerAuth } from '@nestjs/swagger';
import { CameraService } from './camera.service';
import { CreateCameraDto, UpdateCameraDto } from './dto/camera.dto';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';

@ApiTags('Cameras')
@Controller('api/cameras')
@ApiBearerAuth()
export class CameraController {
  constructor(private readonly cameraService: CameraService) {}

  @Post()
  @UseGuards(JwtAuthGuard)
  @ApiOperation({ summary: 'Create a new camera' })
  async create(@Body() createCameraDto: CreateCameraDto) {
    return this.cameraService.create(createCameraDto);
  }

  @Get()
  @UseGuards(JwtAuthGuard)
  @ApiOperation({ summary: 'Get all cameras' })
  async findAll() {
    return this.cameraService.findAll();
  }

  @Get('stats')
  @UseGuards(JwtAuthGuard)
  @ApiOperation({ summary: 'Get camera statistics' })
  async getStats() {
    return this.cameraService.getStats();
  }

  @Get(':id')
  @UseGuards(JwtAuthGuard)
  @ApiOperation({ summary: 'Get a specific camera by ID' })
  async findById(@Param('id') id: string) {
    return this.cameraService.findById(parseInt(id));
  }

  @Put(':id')
  @UseGuards(JwtAuthGuard)
  @ApiOperation({ summary: 'Update a camera' })
  async update(
    @Param('id') id: string,
    @Body() updateCameraDto: UpdateCameraDto
  ) {
    return this.cameraService.update(parseInt(id), updateCameraDto);
  }

  @Delete(':id')
  @UseGuards(JwtAuthGuard)
  @ApiOperation({ summary: 'Delete a camera' })
  async delete(@Param('id') id: string) {
    return this.cameraService.delete(parseInt(id));
  }
}