import {
  IsString,
  IsOptional,
  IsBoolean,
  IsInt,
  IsUrl,
  Min,
  Max,
  IsArray,
  Matches,
} from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';
import { CameraAccessLevel } from '@prisma/client';

export class CreateCameraDto {
  @ApiProperty({ example: 'Main Entrance Camera' })
  @IsString()
  name: string;

  @ApiProperty({ example: 'Main entrance facing the street', required: false })
  @IsOptional()
  @IsString()
  description?: string;

  @ApiProperty({ example: 'Main Entrance' })
  @IsString()
  location: string;

  @ApiProperty({ example: 'rtsp://192.168.1.186:554/Streaming/Channels/101' })
  @Matches(/^rtsp:\/\/.+/, { message: 'rtspUrl must be a valid RTSP URL starting with rtsp://' })
  rtspUrl: string;

  @ApiProperty({ example: 'admin', required: false })
  @IsOptional()
  @IsString()
  username?: string;

  @ApiProperty({ example: 'tt55oo77', required: false })
  @IsOptional()
  @IsString()
  password?: string;

  @ApiProperty({ example: 1 })
  @IsInt()
  companyId: number;

  @ApiProperty({ example: 1, required: false })
  @IsOptional()
  @IsInt()
  adminUserId?: number;

  @ApiProperty({ example: 1920, required: false })
  @IsOptional()
  @IsInt()
  @Min(640)
  @Max(4096)
  resolutionWidth?: number;

  @ApiProperty({ example: 1080, required: false })
  @IsOptional()
  @IsInt()
  @Min(480)
  @Max(2160)
  resolutionHeight?: number;

  @ApiProperty({ example: 30, required: false })
  @IsOptional()
  @IsInt()
  @Min(1)
  @Max(60)
  fps?: number;

  @ApiProperty({ example: 80, required: false })
  @IsOptional()
  @IsInt()
  @Min(1)
  @Max(100)
  quality?: number;

  @ApiProperty({ example: true, required: false })
  @IsOptional()
  @IsBoolean()
  enableMotionDetection?: boolean;

  @ApiProperty({ example: true, required: false })
  @IsOptional()
  @IsBoolean()
  enableRecording?: boolean;

  @ApiProperty({ example: 60, required: false })
  @IsOptional()
  @IsInt()
  @Min(10)
  @Max(3600)
  recordingDuration?: number;
}

export class UpdateCameraDto {
  @ApiProperty({ example: 'Main Entrance Camera', required: false })
  @IsOptional()
  @IsString()
  name?: string;

  @ApiProperty({ example: 'Main entrance facing the street', required: false })
  @IsOptional()
  @IsString()
  description?: string;

  @ApiProperty({ example: 'Main Entrance', required: false })
  @IsOptional()
  @IsString()
  location?: string;

  @ApiProperty({ example: 'rtsp://192.168.1.186:554/Streaming/Channels/101', required: false })
  @IsOptional()
  @Matches(/^rtsp:\/\/.+/, { message: 'rtspUrl must be a valid RTSP URL starting with rtsp://' })
  rtspUrl?: string;

  @ApiProperty({ example: 'admin', required: false })
  @IsOptional()
  @IsString()
  username?: string;

  @ApiProperty({ example: 'tt55oo77', required: false })
  @IsOptional()
  @IsString()
  password?: string;

  @ApiProperty({ example: 1, required: false })
  @IsOptional()
  @IsInt()
  adminUserId?: number;

  @ApiProperty({ example: 1920, required: false })
  @IsOptional()
  @IsInt()
  @Min(640)
  @Max(4096)
  resolutionWidth?: number;

  @ApiProperty({ example: 1080, required: false })
  @IsOptional()
  @IsInt()
  @Min(480)
  @Max(2160)
  resolutionHeight?: number;

  @ApiProperty({ example: 30, required: false })
  @IsOptional()
  @IsInt()
  @Min(1)
  @Max(60)
  fps?: number;

  @ApiProperty({ example: 80, required: false })
  @IsOptional()
  @IsInt()
  @Min(1)
  @Max(100)
  quality?: number;

  @ApiProperty({ example: true, required: false })
  @IsOptional()
  @IsBoolean()
  enableMotionDetection?: boolean;

  @ApiProperty({ example: true, required: false })
  @IsOptional()
  @IsBoolean()
  enableRecording?: boolean;

  @ApiProperty({ example: 60, required: false })
  @IsOptional()
  @IsInt()
  @Min(10)
  @Max(3600)
  recordingDuration?: number;

  @ApiProperty({ example: true, required: false })
  @IsOptional()
  @IsBoolean()
  isActive?: boolean;
}

export class GrantCameraAccessDto {
  @ApiProperty({ example: [1, 2, 3] })
  @IsArray()
  @IsInt({ each: true })
  userIds: number[];

  @ApiProperty({ example: 'VIEWER', enum: CameraAccessLevel })
  @IsString()
  accessLevel: CameraAccessLevel;
}

export class TestCameraConnectionDto {
  @ApiProperty({ example: 'rtsp://192.168.1.186:554/Streaming/Channels/101' })
  @Matches(/^rtsp:\/\/.+/, { message: 'rtspUrl must be a valid RTSP URL starting with rtsp://' })
  rtspUrl: string;

  @ApiProperty({ example: 'admin', required: false })
  @IsOptional()
  @IsString()
  username?: string;

  @ApiProperty({ example: 'tt55oo77', required: false })
  @IsOptional()
  @IsString()
  password?: string;
}
