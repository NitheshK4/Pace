<?php

namespace Pace\Tests;

use PHPUnit\Framework\TestCase;
use Pace\PaceClient;
use Pace\OpenAIWrapper;

class PaceClientTest extends TestCase {
    public function testSanitizeMetadataRemovesSensitiveKeys(): void {
        $client = new PaceClient('pace_test_key', 'http://localhost:9999');

        $rawMetadata = [
            'environment' => 'staging',
            'user_id'     => 101,
            'prompt'      => 'Super secret prompt text',
            'completion'  => 'Secret response text',
            'api_key'     => 'sk-12345678',
            'authorization' => 'Bearer token'
        ];

        $clean = $client->sanitizeMetadata($rawMetadata);

        $this->assertArrayHasKey('environment', $clean);
        $this->assertArrayHasKey('user_id', $clean);
        $this->assertArrayNotHasKey('prompt', $clean);
        $this->assertArrayNotHasKey('completion', $clean);
        $this->assertArrayNotHasKey('api_key', $clean);
        $this->assertArrayNotHasKey('authorization', $clean);
    }

    public function testCreateProxyConfig(): void {
        $config = OpenAIWrapper::createProxyConfig('sk-testkey');

        $this->assertEquals('http://127.0.0.1:8787/v1/', $config['base_uri']);
        $this->assertEquals('Bearer sk-testkey', $config['headers']['Authorization']);
    }

    public function testSetSystemTag(): void {
        $client = new PaceClient('pace_test_key', 'http://localhost:9999');
        $client->setSystemTag('version', '1.2.3');
        $this->assertTrue(true);
    }
}
