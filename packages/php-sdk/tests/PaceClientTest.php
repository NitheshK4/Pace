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

    public function testClientGetters(): void {
        $client = new PaceClient('pace_test_key', 'http://localhost:9999/', 5);
        $this->assertEquals('http://localhost:9999', $client->getEndpoint());
        $this->assertEquals(5, $client->getTimeout());
    }

    public function testSetTimeoutValidatesValue(): void {
        $client = new PaceClient('pace_test_key', 'http://localhost:9999', 5);
        $client->setTimeout(10);
        $this->assertEquals(10, $client->getTimeout());

        $caught = false;
        try {
            $client->setTimeout(0);
        } catch (\InvalidArgumentException $e) {
            $caught = true;
        }
        $this->assertTrue($caught, 'Should throw InvalidArgumentException on zero timeout');
    }

    public function testRecordBatchValidatesEvents(): void {
        $client = new PaceClient('pace_test_key', 'http://localhost:9999');
        $res = $client->recordBatch([
            ['invalid' => 'no_provider_or_model'],
            ['provider' => 'openai']
        ]);
        $this->assertFalse($res['success']);
        $this->assertEquals(400, $res['status']);
        $this->assertEquals('No valid events to submit', $res['error']);
    }

    public function testCustomHeadersConfiguration(): void {
        $client = new PaceClient('pace_test_key', 'http://localhost:9999');
        $client->setCustomHeader('X-Environment', 'staging');
        $headers = $client->getCustomHeaders();
        $this->assertArrayHasKey('X-Environment', $headers);
        $this->assertEquals('staging', $headers['X-Environment']);
    }

    public function testRetryAttemptsConfiguration(): void {
        $client = new PaceClient('pace_test_key', 'http://localhost:9999');
        $this->assertEquals(3, $client->getRetryAttempts());

        $client->setRetryAttempts(5);
        $this->assertEquals(5, $client->getRetryAttempts());

        $caught = false;
        try {
            $client->setRetryAttempts(0);
        } catch (\InvalidArgumentException $e) {
            $caught = true;
        }
        $this->assertTrue($caught, 'Should throw InvalidArgumentException on zero retry attempts');
    }
}
