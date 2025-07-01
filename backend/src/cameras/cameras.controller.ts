import {
  Controller,
  Get,
  Post,
  Body,
  Patch,
  Param,
  Delete,
  UseGuards,
  Request,
  ParseIntPipe,
} from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiBearerAuth } from '@nestjs/swagger';
import { CamerasService } from './cameras.service';
import { 
  CreateCameraDto, 
  UpdateCameraDto, 
  GrantCameraAccessDto,
  TestCameraConnectionDto 
} from './dto/camera.dto';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';

@ApiTags('Cameras')
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller('cameras')
export class CamerasController {
  constructor(private readonly camerasService: CamerasService) {}

  @Post()
  @ApiOperation({ summary: 'Create a new camera' })
  @ApiResponse({ status: 201, description: 'Camera created successfully' })
  @ApiResponse({ status: 403, description: 'Access denied' })
  @ApiResponse({ status: 400, description: 'Camera URL already exists' })
  create(@Body() createCameraDto: CreateCameraDto, @Request() req) {
    return this.camerasService.create(createCameraDto, req.user.userId);
  }

  @Get()
  @ApiOperation({ summary: 'Get all accessible cameras' })
  @ApiResponse({ status: 200, description: 'Cameras retrieved successfully' })
  findAll(@Request() req) {
    return this.camerasService.findAll(req.user.userId);
  }

  @Get(':id')
  @ApiOperation({ summary: 'Get a specific camera' })
  @ApiResponse({ status: 200, description: 'Camera retrieved successfully' })
  @ApiResponse({ status: 404, description: 'Camera not found' })
  @ApiResponse({ status: 403, description: 'Access denied' })
  findOne(@Param('id', ParseIntPipe) id: number, @Request() req) {
    return this.camerasService.findOne(id, req.user.userId);
  }

  @Patch(':id')
  @ApiOperation({ summary: 'Update a camera' })
  @ApiResponse({ status: 200, description: 'Camera updated successfully' })
  @ApiResponse({ status: 404, description: 'Camera not found' })
  @ApiResponse({ status: 403, description: 'Access denied' })
  update(
    @Param('id', ParseIntPipe) id: number,
    @Body() updateCameraDto: UpdateCameraDto,
    @Request() req,
  ) {
    return this.camerasService.update(id, updateCameraDto, req.user.userId);
  }

  @Delete(':id')
  @ApiOperation({ summary: 'Delete a camera' })
  @ApiResponse({ status: 200, description: 'Camera deleted successfully' })
  @ApiResponse({ status: 404, description: 'Camera not found' })
  @ApiResponse({ status: 403, description: 'Access denied' })
  remove(@Param('id', ParseIntPipe) id: number, @Request() req) {
    return this.camerasService.remove(id, req.user.userId);
  }

  @Post(':id/access')
  @ApiOperation({ summary: 'Grant camera access to users' })
  @ApiResponse({ status: 201, description: 'Access granted successfully' })
  @ApiResponse({ status: 404, description: 'Camera not found' })
  @ApiResponse({ status: 403, description: 'Access denied' })
  grantAccess(
    @Param('id', ParseIntPipe) id: number,
    @Body() grantAccessDto: GrantCameraAccessDto,
    @Request() req,
  ) {
    return this.camerasService.grantAccess(id, grantAccessDto, req.user.userId);
  }

  @Delete(':id/access/:userId')
  @ApiOperation({ summary: 'Revoke camera access from a user' })
  @ApiResponse({ status: 200, description: 'Access revoked successfully' })
  @ApiResponse({ status: 404, description: 'Camera not found' })
  @ApiResponse({ status: 403, description: 'Access denied' })
  revokeAccess(
    @Param('id', ParseIntPipe) id: number,
    @Param('userId', ParseIntPipe) targetUserId: number,
    @Request() req,
  ) {
    return this.camerasService.revokeAccess(id, targetUserId, req.user.userId);
  }

  @Post('test-connection')
  @ApiOperation({ summary: 'Test camera RTSP connection' })
  @ApiResponse({ status: 200, description: 'Connection test completed' })
  testConnection(@Body() testDto: TestCameraConnectionDto) {
    return this.camerasService.testConnection(testDto);
  }
}
