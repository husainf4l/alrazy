import { IsString, IsOptional, IsEmail, IsUrl, IsBoolean } from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';

export class CreateCompanyDto {
  @ApiProperty({ example: 'Al Razy Pharmacy' })
  @IsString()
  name: string;

  @ApiProperty({ example: 'Leading pharmacy chain in Saudi Arabia', required: false })
  @IsOptional()
  @IsString()
  description?: string;

  @ApiProperty({ example: 'Riyadh, Saudi Arabia', required: false })
  @IsOptional()
  @IsString()
  address?: string;

  @ApiProperty({ example: '+966123456789', required: false })
  @IsOptional()
  @IsString()
  phone?: string;

  @ApiProperty({ example: 'info@alrazy.com', required: false })
  @IsOptional()
  @IsEmail()
  email?: string;

  @ApiProperty({ example: 'https://alrazy.com', required: false })
  @IsOptional()
  @IsUrl()
  website?: string;
}

export class UpdateCompanyDto {
  @ApiProperty({ example: 'Al Razy Pharmacy', required: false })
  @IsOptional()
  @IsString()
  name?: string;

  @ApiProperty({ example: 'Leading pharmacy chain in Saudi Arabia', required: false })
  @IsOptional()
  @IsString()
  description?: string;

  @ApiProperty({ example: 'Riyadh, Saudi Arabia', required: false })
  @IsOptional()
  @IsString()
  address?: string;

  @ApiProperty({ example: '+966123456789', required: false })
  @IsOptional()
  @IsString()
  phone?: string;

  @ApiProperty({ example: 'info@alrazy.com', required: false })
  @IsOptional()
  @IsEmail()
  email?: string;

  @ApiProperty({ example: 'https://alrazy.com', required: false })
  @IsOptional()
  @IsUrl()
  website?: string;

  @ApiProperty({ example: true, required: false })
  @IsOptional()
  @IsBoolean()
  isActive?: boolean;
}
