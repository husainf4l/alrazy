import { IsNotEmpty, IsString, IsOptional, IsUrl } from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';

export class CreateCameraDto {
  @ApiProperty({ description: 'Camera name' })
  @IsNotEmpty()
  @IsString()
  name: string;

  @ApiProperty({ 
    description: 'Camera location/zone',
    required: false 
  })
  @IsOptional()
  @IsString()
  location?: string;

  @ApiProperty({ 
    description: 'RTSP or HTTP stream URL',
    required: false 
  })
  @IsOptional()
  @IsString()
  streamUrl?: string;

  @ApiProperty({ 
    description: 'WebRTC URL for real-time viewing',
    required: false 
  })
  @IsOptional()
  @IsString()
  webrtcUrl?: string;

  @ApiProperty({ 
    description: 'Camera description',
    required: false 
  })
  @IsOptional()
  @IsString()
  description?: string;
}

export class UpdateCameraDto {
  @ApiProperty({ 
    description: 'Camera name',
    required: false 
  })
  @IsOptional()
  @IsString()
  name?: string;

  @ApiProperty({ 
    description: 'Camera location/zone',
    required: false 
  })
  @IsOptional()
  @IsString()
  location?: string;

  @ApiProperty({ 
    description: 'RTSP or HTTP stream URL',
    required: false 
  })
  @IsOptional()
  @IsString()
  streamUrl?: string;

  @ApiProperty({ 
    description: 'WebRTC URL for real-time viewing',
    required: false 
  })
  @IsOptional()
  @IsString()
  webrtcUrl?: string;

  @ApiProperty({ 
    description: 'Camera description',
    required: false 
  })
  @IsOptional()
  @IsString()
  description?: string;

  @ApiProperty({ 
    description: 'Camera active status',
    required: false 
  })
  @IsOptional()
  isActive?: boolean;
}