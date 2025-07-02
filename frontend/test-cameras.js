/**
 * Camera Dashboard Test Suite
 * Node.js script to test camera connectivity and API endpoints
 */

const http = require('http');
const net = require('net');

const CAMERA_IP = '149.200.251.12';
const CAMERA_PORTS = [554, 555, 556, 557];
const CAMERA_NAMES = ['Main Security Camera', 'Secondary Camera', 'Backup Camera', 'Auxiliary Camera'];
const API_BASE = 'http://localhost:3000/api';

// Colors for console output
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  bold: '\x1b[1m'
};

function colorLog(color, message) {
  console.log(color + message + colors.reset);
}

function testResult(testName, passed, details = '') {
  const icon = passed ? '✅' : '❌';
  const color = passed ? colors.green : colors.red;
  colorLog(color, `${icon} ${testName}: ${passed ? 'PASS' : 'FAIL'} ${details}`);
}

// Test network connectivity
async function testNetworkConnectivity() {
  colorLog(colors.blue, '\n📡 Testing Network Connectivity...');
  
  return new Promise((resolve) => {
    const { spawn } = require('child_process');
    const ping = spawn('ping', ['-c', '3', '-W', '1000', CAMERA_IP]);
    
    ping.on('close', (code) => {
      const passed = code === 0;
      testResult('Network Ping', passed, `Camera IP ${CAMERA_IP} ${passed ? 'is reachable' : 'is not reachable'}`);
      resolve(passed);
    });
  });
}

// Test port connectivity
async function testPortConnectivity() {
  colorLog(colors.blue, '\n🔌 Testing Port Connectivity...');
  
  const results = [];
  
  for (let i = 0; i < CAMERA_PORTS.length; i++) {
    const port = CAMERA_PORTS[i];
    const cameraName = CAMERA_NAMES[i];
    
    const isOpen = await new Promise((resolve) => {
      const socket = new net.Socket();
      const timeout = setTimeout(() => {
        socket.destroy();
        resolve(false);
      }, 5000);
      
      socket.connect(port, CAMERA_IP, () => {
        clearTimeout(timeout);
        socket.destroy();
        resolve(true);
      });
      
      socket.on('error', () => {
        clearTimeout(timeout);
        resolve(false);
      });
    });
    
    testResult(`Port ${port} (${cameraName})`, isOpen, isOpen ? 'Port is open' : 'Port is closed or inaccessible');
    results.push(isOpen);
  }
  
  return results;
}

// Test API endpoints
async function testAPIEndpoints() {
  colorLog(colors.blue, '\n🔗 Testing API Endpoints...');
  
  // Check if server is running
  const serverRunning = await new Promise((resolve) => {
    const req = http.get('http://localhost:3000', (res) => {
      resolve(true);
    });
    
    req.on('error', () => {
      resolve(false);
    });
    
    req.setTimeout(5000, () => {
      req.destroy();
      resolve(false);
    });
  });
  
  testResult('Next.js Server', serverRunning, serverRunning ? 'Server is running' : 'Server is not running');
  
  if (!serverRunning) {
    colorLog(colors.yellow, '⚠️  Start server with: npm run dev');
    return false;
  }
  
  // Test camera connection API
  const apiResults = [];
  
  for (let i = 0; i < CAMERA_PORTS.length; i++) {
    const port = CAMERA_PORTS[i];
    const cameraId = `cam${i + 1}`;
    
    const testData = JSON.stringify({
      ip: CAMERA_IP,
      port: port,
      username: 'admin',
      password: 'admin123',
      cameraId: cameraId
    });
    
    const result = await new Promise((resolve) => {
      const postReq = http.request({
        hostname: 'localhost',
        port: 3000,
        path: '/api/test-camera-connection',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(testData)
        }
      }, (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          try {
            const response = JSON.parse(data);
            resolve({
              success: res.statusCode === 200 && response.success === true,
              response: response
            });
          } catch (e) {
            resolve({ success: false, response: { error: 'Invalid JSON response' } });
          }
        });
      });
      
      postReq.on('error', (error) => {
        resolve({ success: false, response: { error: error.message } });
      });
      
      postReq.setTimeout(10000, () => {
        postReq.destroy();
        resolve({ success: false, response: { error: 'Request timeout' } });
      });
      
      postReq.write(testData);
      postReq.end();
    });
    
    testResult(
      `API Test - Camera ${i + 1}`, 
      result.success,
      result.success ? 'Connection test successful' : `Error: ${result.response.error || 'Unknown error'}`
    );
    
    apiResults.push(result.success);
  }
  
  return apiResults;
}

// Test file existence
async function testFiles() {
  colorLog(colors.blue, '\n📁 Testing Component Files...');
  
  const fs = require('fs');
  const path = require('path');
  
  // Check enhanced component
  const enhancedComponentPath = path.join(__dirname, 'src/components/CameraStreamGridEnhanced.tsx');
  const enhancedExists = fs.existsSync(enhancedComponentPath);
  
  if (enhancedExists) {
    const stats = fs.statSync(enhancedComponentPath);
    testResult('Enhanced Component', stats.size > 1000, `File size: ${stats.size} bytes`);
  } else {
    testResult('Enhanced Component', false, 'File not found');
  }
  
  // Check dashboard page
  const dashboardPath = path.join(__dirname, 'src/app/dashboard/page.tsx');
  const dashboardExists = fs.existsSync(dashboardPath);
  
  if (dashboardExists) {
    const content = fs.readFileSync(dashboardPath, 'utf8');
    const hasImport = content.includes('CameraStreamGridEnhanced');
    testResult('Dashboard Integration', hasImport, hasImport ? 'Imports enhanced component' : 'Missing enhanced component import');
  } else {
    testResult('Dashboard Integration', false, 'Dashboard file not found');
  }
}

// Main test function
async function runTests() {
  colorLog(colors.bold + colors.blue, '🎥 Camera Dashboard Test Suite');
  colorLog(colors.bold + colors.blue, '================================');
  console.log(`Camera IP: ${CAMERA_IP}`);
  console.log(`Test Time: ${new Date().toISOString()}`);
  
  let totalTests = 0;
  let passedTests = 0;
  
  // Run all tests
  const networkResult = await testNetworkConnectivity();
  totalTests++; if (networkResult) passedTests++;
  
  const portResults = await testPortConnectivity();
  totalTests += portResults.length;
  passedTests += portResults.filter(r => r).length;
  
  const apiResults = await testAPIEndpoints();
  if (Array.isArray(apiResults)) {
    totalTests += apiResults.length;
    passedTests += apiResults.filter(r => r).length;
  }
  
  await testFiles();
  totalTests += 2; // Two file tests
  
  // Summary
  colorLog(colors.blue, '\n📊 Test Summary');
  colorLog(colors.blue, '===============');
  colorLog(colors.green, `✅ Passed: ${passedTests}`);
  colorLog(colors.red, `❌ Failed: ${totalTests - passedTests}`);
  
  if (passedTests === totalTests) {
    colorLog(colors.green, '\n🎉 All tests passed! Camera dashboard should be working.');
  } else {
    colorLog(colors.yellow, '\n⚠️  Some tests failed. Check the issues above.');
  }
  
  // Manual testing instructions
  colorLog(colors.blue, '\n🧪 Manual Testing Instructions:');
  colorLog(colors.blue, '================================');
  console.log('1. Start the development server:');
  console.log('   npm run dev');
  console.log('');
  console.log('2. Open browser to: http://localhost:3000/dashboard');
  console.log('');
  console.log('3. Test camera functionality:');
  console.log('   - Click "Start" button on each camera');
  console.log('   - Check connection status indicators');
  console.log('   - Test fullscreen mode (expand button)');
  console.log('   - Verify error handling (if cameras fail)');
  console.log('');
  console.log('4. Monitor system status at bottom of dashboard');
  console.log('');
}

// Run the tests
if (require.main === module) {
  runTests().catch(console.error);
}

module.exports = {
  runTests,
  testNetworkConnectivity,
  testPortConnectivity,
  testAPIEndpoints,
  testFiles
};
