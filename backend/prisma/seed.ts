import { PrismaClient, UserRole } from '@prisma/client';
import * as bcrypt from 'bcryptjs';

const prisma = new PrismaClient();

async function main() {
  console.log('🌱 Starting database seeding...');

  // Create Al Razy company
  const company = await prisma.company.upsert({
    where: { id: 1 },
    update: {},
    create: {
      name: 'Al Razy Pharmacy',
      description: 'Leading pharmacy chain in Saudi Arabia',
      address: 'Riyadh, Saudi Arabia',
      phone: '+966123456789',
      email: 'info@alrazy.com',
      website: 'https://alrazy.com',
    },
  });

  console.log('✅ Created company:', company.name);

  // Create super admin user
  const hashedPassword = await bcrypt.hash('tt55oo77', 12);
  
  const superAdmin = await prisma.user.upsert({
    where: { email: 'husain@alrazy.com' },
    update: {},
    create: {
      email: 'husain@alrazy.com',
      username: 'husain',
      password: hashedPassword,
      firstName: 'Husain',
      lastName: 'Al Razy',
      phone: '+966501234567',
      role: UserRole.SUPER_ADMIN,
      companyId: company.id,
    },
  });

  console.log('✅ Created super admin user:', superAdmin.username);

  // Create company admin user
  const companyAdmin = await prisma.user.upsert({
    where: { email: 'admin@alrazy.com' },
    update: {},
    create: {
      email: 'admin@alrazy.com',
      username: 'admin',
      password: hashedPassword,
      firstName: 'Admin',
      lastName: 'User',
      role: UserRole.COMPANY_ADMIN,
      companyId: company.id,
    },
  });

  console.log('✅ Created company admin user:', companyAdmin.username);

  // Create regular user
  const regularUser = await prisma.user.upsert({
    where: { email: 'user@alrazy.com' },
    update: {},
    create: {
      email: 'user@alrazy.com',
      username: 'user',
      password: hashedPassword,
      firstName: 'Regular',
      lastName: 'User',
      role: UserRole.USER,
      companyId: company.id,
    },
  });

  console.log('✅ Created regular user:', regularUser.username);

  // Create sample cameras
  const cameras = [
    {
      name: 'Main Entrance Camera',
      description: 'Camera monitoring the main entrance',
      location: 'Main Entrance',
      rtspUrl: 'rtsp://192.168.1.186:554/Streaming/Channels/101',
      webRtcUrl: 'https://webrtc.alrazy.com/stream/entrance',
      username: 'admin',
      password: 'tt55oo77',
      companyId: company.id,
      adminUserId: companyAdmin.id,
    },
    {
      name: 'Pharmacy Floor Camera',
      description: 'Camera monitoring the pharmacy floor',
      location: 'Pharmacy Floor',
      rtspUrl: 'rtsp://192.168.1.186:554/Streaming/Channels/201',
      webRtcUrl: 'https://webrtc.alrazy.com/stream/pharmacy',
      username: 'admin',
      password: 'tt55oo77',
      companyId: company.id,
      adminUserId: companyAdmin.id,
    },
    {
      name: 'Storage Room Camera',
      description: 'Camera monitoring the storage room',
      location: 'Storage Room',
      rtspUrl: 'rtsp://192.168.1.186:554/Streaming/Channels/301',
      username: 'admin',
      password: 'tt55oo77',
      companyId: company.id,
      adminUserId: companyAdmin.id,
    },
    {
      name: 'Back Exit Camera',
      description: 'Camera monitoring the back exit',
      location: 'Back Exit',
      rtspUrl: 'rtsp://192.168.1.186:554/Streaming/Channels/401',
      username: 'admin',
      password: 'tt55oo77',
      companyId: company.id,
      adminUserId: companyAdmin.id,
    },
  ];

  for (const cameraData of cameras) {
    const existingCamera = await prisma.camera.findFirst({
      where: { rtspUrl: cameraData.rtspUrl },
    });

    if (existingCamera) {
      console.log('⚠️ Camera already exists:', cameraData.name);
      continue;
    }

    const camera = await prisma.camera.create({
      data: cameraData,
    });
    console.log('✅ Created camera:', camera.name);

    // Grant access to regular user
    await prisma.cameraUserAccess.upsert({
      where: {
        cameraId_userId: {
          cameraId: camera.id,
          userId: regularUser.id,
        },
      },
      update: {},
      create: {
        cameraId: camera.id,
        userId: regularUser.id,
        accessLevel: 'VIEWER',
        grantedBy: companyAdmin.id,
      },
    });
  }

  console.log('🎉 Database seeding completed successfully!');
  console.log('\n📝 Login credentials:');
  console.log('Super Admin: husain@alrazy.com / tt55oo77');
  console.log('Company Admin: admin@alrazy.com / tt55oo77');
  console.log('Regular User: user@alrazy.com / tt55oo77');
}

main()
  .then(async () => {
    await prisma.$disconnect();
  })
  .catch(async (e) => {
    console.error('❌ Seeding failed:', e);
    await prisma.$disconnect();
    process.exit(1);
  });
