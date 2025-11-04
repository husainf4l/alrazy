import { PrismaClient } from '@prisma/client';
import * as bcrypt from 'bcryptjs';

const prisma = new PrismaClient();

async function main() {
  console.log('🌱 Starting database seeding...');

  const hashedPassword = await bcrypt.hash('password123', 10);
  
  const admin = await prisma.user.upsert({
    where: { email: 'admin@security.com' },
    update: {},
    create: {
      email: 'admin@security.com',
      username: 'admin',
      password: hashedPassword,
      firstName: 'Admin',
      lastName: 'User',
      role: 'ADMIN',
      isActive: true,
    },
  });

  console.log('✅ Created admin user:', admin.username);

  const user = await prisma.user.upsert({
    where: { email: 'user@security.com' },
    update: {},
    create: {
      email: 'user@security.com',
      username: 'user',
      password: hashedPassword,
      firstName: 'Regular',
      lastName: 'User',
      role: 'USER',
      isActive: true,
    },
  });

  console.log('✅ Created regular user:', user.username);

  const cameras = [
    {
      name: 'Main Entrance',
      location: 'Main Entrance',
      streamUrl: 'rtsp://192.168.1.100:554/stream',
      webrtcUrl: 'webrtc://192.168.1.100/stream',
      description: 'Main entrance camera',
      isActive: true,
    },
    {
      name: 'Back Door',
      location: 'Back Exit',
      streamUrl: 'rtsp://192.168.1.101:554/stream',
      webrtcUrl: 'webrtc://192.168.1.101/stream',
      description: 'Back exit camera',
      isActive: true,
    },
    {
      name: 'Floor Monitor',
      location: 'Main Floor',
      streamUrl: 'rtsp://192.168.1.102:554/stream',
      webrtcUrl: 'webrtc://192.168.1.102/stream',
      description: 'Main floor monitoring camera',
      isActive: true,
    },
  ];

  for (const cameraData of cameras) {
    const existingCamera = await prisma.camera.findFirst({
      where: { name: cameraData.name },
    });

    if (existingCamera) {
      console.log('⚠️  Camera already exists:', cameraData.name);
      continue;
    }

    const camera = await prisma.camera.create({
      data: cameraData,
    });
    console.log('✅ Created camera:', camera.name);
  }

  console.log('✨ Database seeding completed successfully!');
}

main()
  .catch((e) => {
    console.error('❌ Error during seeding:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
