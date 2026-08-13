<?php

spl_autoload_register(function ($class) {
    $prefix = 'Pace\\';
    $baseDir = __DIR__ . '/src/';
    $len = strlen($prefix);
    if (strncmp($prefix, $class, $len) !== 0) {
        return;
    }
    $relativeClass = substr($class, $len);
    $file = $baseDir . str_replace('\\', '/', $relativeClass) . '.php';
    if (file_exists($file)) {
        require $file;
    }
});

spl_autoload_register(function ($class) {
    $prefix = 'Pace\\Tests\\';
    $baseDir = __DIR__ . '/tests/';
    $len = strlen($prefix);
    if (strncmp($prefix, $class, $len) !== 0) {
        return;
    }
    $relativeClass = substr($class, $len);
    $file = $baseDir . str_replace('\\', '/', $relativeClass) . '.php';
    if (file_exists($file)) {
        require $file;
    }
});

if (!class_exists('PHPUnit\\Framework\\TestCase')) {
    eval('
    namespace PHPUnit\\Framework;
    class TestCase {
        protected function assertEquals($expected, $actual, string $message = ""): void {
            if ($expected != $actual) {
                throw new \Exception("Failed asserting that " . json_encode($actual) . " matches expected " . json_encode($expected) . ". $message");
            }
        }
        protected function assertSame($expected, $actual, string $message = ""): void {
            if ($expected !== $actual) {
                throw new \Exception("Failed asserting that " . json_encode($actual) . " is identical to " . json_encode($expected) . ". $message");
            }
        }
        protected function assertTrue($condition, string $message = ""): void {
            if ($condition !== true) {
                throw new \Exception("Failed asserting that value is true. $message");
            }
        }
        protected function assertFalse($condition, string $message = ""): void {
            if ($condition !== false) {
                throw new \Exception("Failed asserting that value is false. $message");
            }
        }
        protected function assertArrayHasKey($key, $array, string $message = ""): void {
            if (!is_array($array) || !array_key_exists($key, $array)) {
                throw new \Exception("Failed asserting that array has key \'$key\'. $message");
            }
        }
        protected function assertArrayNotHasKey($key, $array, string $message = ""): void {
            if (is_array($array) && array_key_exists($key, $array)) {
                throw new \Exception("Failed asserting that array does NOT have key \'$key\'. $message");
            }
        }
        protected function assertNull($actual, string $message = ""): void {
            if ($actual !== null) {
                throw new \Exception("Failed asserting that " . json_encode($actual) . " is null. $message");
            }
        }
    }
    ');
}

$passed = 0;
$testFiles = glob(__DIR__ . '/tests/*Test.php');
foreach ($testFiles as $file) {
    require_once $file;
    $className = 'Pace\\Tests\\' . basename($file, '.php');
    if (class_exists($className)) {
        $reflection = new ReflectionClass($className);
        if (!$reflection->isAbstract()) {
            $instance = new $className();
            foreach ($reflection->getMethods(ReflectionMethod::IS_PUBLIC) as $method) {
                if (str_starts_with($method->name, 'test')) {
                    echo "Running {$className}::{$method->name}... ";
                    $instance->{$method->name}();
                    echo "OK\n";
                    $passed++;
                }
            }
        }
    }
}
echo "\nAll {$passed} PHP SDK tests passed successfully.\n";
