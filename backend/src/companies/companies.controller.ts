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
import { CompaniesService } from './companies.service';
import { CreateCompanyDto, UpdateCompanyDto } from './dto/company.dto';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';

@ApiTags('Companies')
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller('companies')
export class CompaniesController {
  constructor(private readonly companiesService: CompaniesService) {}

  @Post()
  @ApiOperation({ summary: 'Create a new company (Super Admin only)' })
  @ApiResponse({ status: 201, description: 'Company created successfully' })
  @ApiResponse({ status: 403, description: 'Access denied' })
  create(@Body() createCompanyDto: CreateCompanyDto, @Request() req) {
    return this.companiesService.create(createCompanyDto, req.user.userId);
  }

  @Get()
  @ApiOperation({ summary: 'Get all companies' })
  @ApiResponse({ status: 200, description: 'Companies retrieved successfully' })
  findAll(@Request() req) {
    return this.companiesService.findAll(req.user.userId);
  }

  @Get(':id')
  @ApiOperation({ summary: 'Get a specific company' })
  @ApiResponse({ status: 200, description: 'Company retrieved successfully' })
  @ApiResponse({ status: 404, description: 'Company not found' })
  @ApiResponse({ status: 403, description: 'Access denied' })
  findOne(@Param('id', ParseIntPipe) id: number, @Request() req) {
    return this.companiesService.findOne(id, req.user.userId);
  }

  @Patch(':id')
  @ApiOperation({ summary: 'Update a company' })
  @ApiResponse({ status: 200, description: 'Company updated successfully' })
  @ApiResponse({ status: 404, description: 'Company not found' })
  @ApiResponse({ status: 403, description: 'Access denied' })
  update(
    @Param('id', ParseIntPipe) id: number,
    @Body() updateCompanyDto: UpdateCompanyDto,
    @Request() req,
  ) {
    return this.companiesService.update(id, updateCompanyDto, req.user.userId);
  }

  @Delete(':id')
  @ApiOperation({ summary: 'Delete a company (Super Admin only)' })
  @ApiResponse({ status: 200, description: 'Company deleted successfully' })
  @ApiResponse({ status: 404, description: 'Company not found' })
  @ApiResponse({ status: 403, description: 'Access denied' })
  remove(@Param('id', ParseIntPipe) id: number, @Request() req) {
    return this.companiesService.remove(id, req.user.userId);
  }

  @Get(':id/users')
  @ApiOperation({ summary: 'Get all users in a company' })
  @ApiResponse({ status: 200, description: 'Company users retrieved successfully' })
  @ApiResponse({ status: 403, description: 'Access denied' })
  getCompanyUsers(@Param('id', ParseIntPipe) id: number, @Request() req) {
    return this.companiesService.getCompanyUsers(id, req.user.userId);
  }

  @Get(':id/cameras')
  @ApiOperation({ summary: 'Get all cameras in a company' })
  @ApiResponse({ status: 200, description: 'Company cameras retrieved successfully' })
  @ApiResponse({ status: 403, description: 'Access denied' })
  @ApiResponse({ status: 404, description: 'Company not found' })
  getCompanyCameras(@Param('id', ParseIntPipe) id: number, @Request() req) {
    return this.companiesService.getCompanyCameras(id, req.user.userId);
  }
}
