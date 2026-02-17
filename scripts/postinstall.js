#!/usr/bin/env node

const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

const projectRoot = path.join(__dirname, '..');

console.log('\n📦 Setting up Claude Session Analyzer...\n');

// Check Python
try {
  execSync('python3 --version', { stdio: 'pipe' });
  console.log('✓ Python 3 found');
} catch (e) {
  console.error('✗ Python 3 is required but not installed.');
  console.error('  Please install Python 3.10+ and try again.');
  process.exit(1);
}

// Check pip
try {
  execSync('pip3 --version', { stdio: 'pipe' });
  console.log('✓ pip found');
} catch (e) {
  console.error('✗ pip is required but not installed.');
  process.exit(1);
}

// Install Python dependencies
const pyprojectPath = path.join(projectRoot, 'pyproject.toml');

if (fs.existsSync(pyprojectPath)) {
  console.log('\n📦 Installing Python dependencies...\n');
  try {
    execSync(`pip3 install "${projectRoot}"`, { stdio: 'inherit' });
    console.log('\n✓ Dependencies installed');
  } catch (e) {
    console.error('✗ Failed to install Python dependencies');
    process.exit(1);
  }
}

// Install Skill to ~/.claude/skills/
const claudeDir = path.join(os.homedir(), '.claude');
const skillsDir = path.join(claudeDir, 'skills');
const skillSourceDir = path.join(projectRoot, 'skills', 'session-search');
const skillDestDir = path.join(skillsDir, 'session-search');

// Create skills directory if it doesn't exist
if (!fs.existsSync(skillsDir)) {
  fs.mkdirSync(skillsDir, { recursive: true });
  console.log(`✓ Created skills directory: ${skillsDir}`);
}

// Create skill directory
if (!fs.existsSync(skillDestDir)) {
  fs.mkdirSync(skillDestDir, { recursive: true });
}

// Copy skill files
try {
  const files = fs.readdirSync(skillSourceDir);
  for (const file of files) {
    const src = path.join(skillSourceDir, file);
    const dest = path.join(skillDestDir, file);
    fs.copyFileSync(src, dest);
  }
  console.log(`✓ Installed skill: session-search`);
} catch (e) {
  console.error(`✗ Failed to install skill: ${e.message}`);
}

console.log('\n✨ Claude Session Analyzer is ready!\n');
console.log('Usage:');
console.log('  /session-search <query>   - Search conversations in Claude Code');
console.log('  csa analyze <file.jsonl>  - Analyze a session file');
console.log('  csa search <query>        - Search from command line\n');
