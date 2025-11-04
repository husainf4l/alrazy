import { IsNotEmpty, IsInt, IsOptional, IsString, IsNumber, Min } from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';

export class CreateEventDto {
  @ApiProperty({ description: 'Camera ID that detected the event' })
  @IsNotEmpty()
  @IsInt()
  cameraId: number;

  @ApiProperty({ 
    description: 'Number of persons detected',
    minimum: 0,
    default: 1 
  })
  @IsInt()
  @Min(0)
  personCount: number;

  @ApiProperty({ 
    description: 'AI detection confidence (0.0 - 1.0)',
    required: false 
  })
  @IsOptional()
  @IsNumber()
  confidence?: number;

  @ApiProperty({ 
    description: 'Path to saved snapshot image',
    required: false 
  })
  @IsOptional()
  @IsString()
  snapshotPath?: string;

  @ApiProperty({ 
    description: 'Additional event description',
    required: false 
  })
  @IsOptional()
  @IsString()
  description?: string;
}

export class EventResponseDto {
  id: number;
  cameraId: number;
  eventType: string;
  personCount: number;
  confidence?: number;
  snapshotPath?: string;
  description?: string;
  isResolved: boolean;
  createdAt: Date;
  resolvedAt?: Date;
  camera: {
    id: number;
    name: string;
    location?: string;
  };
}