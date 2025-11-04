import { Controller, Get, Post, Body, Param, Patch, Query, UseGuards, Req } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiBearerAuth } from '@nestjs/swagger';
import { EventService } from './event.service';
import { CreateEventDto } from './dto/event.dto';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';

@ApiTags('Events')
@Controller('api/events')
@ApiBearerAuth()
export class EventController {
  constructor(private readonly eventService: EventService) {}

  @Post()
  @ApiOperation({ summary: 'Create a new event (typically from AI engine)' })
  async create(@Body() createEventDto: CreateEventDto) {
    return this.eventService.create(createEventDto);
  }

  @Get()
  @UseGuards(JwtAuthGuard)
  @ApiOperation({ summary: 'Get all events with pagination' })
  async findAll(
    @Query('limit') limit: string = '50',
    @Query('offset') offset: string = '0'
  ) {
    return this.eventService.findAll(parseInt(limit), parseInt(offset));
  }

  @Get('unresolved')
  @UseGuards(JwtAuthGuard)
  @ApiOperation({ summary: 'Get all unresolved events' })
  async findUnresolved() {
    return this.eventService.findUnresolved();
  }

  @Get('stats')
  @UseGuards(JwtAuthGuard)
  @ApiOperation({ summary: 'Get event statistics' })
  async getStats() {
    return this.eventService.getEventStats();
  }

  @Get('camera/:cameraId')
  @UseGuards(JwtAuthGuard)
  @ApiOperation({ summary: 'Get events for a specific camera' })
  async findByCamera(
    @Param('cameraId') cameraId: string,
    @Query('limit') limit: string = '50'
  ) {
    return this.eventService.findByCamera(parseInt(cameraId), parseInt(limit));
  }

  @Get(':id')
  @UseGuards(JwtAuthGuard)
  @ApiOperation({ summary: 'Get a specific event by ID' })
  async findById(@Param('id') id: string) {
    return this.eventService.findById(parseInt(id));
  }

  @Patch(':id/resolve')
  @UseGuards(JwtAuthGuard)
  @ApiOperation({ summary: 'Mark an event as resolved' })
  async resolve(@Param('id') id: string) {
    return this.eventService.resolve(parseInt(id));
  }
}