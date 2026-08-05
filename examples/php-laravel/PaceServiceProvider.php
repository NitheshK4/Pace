<?php

namespace App\Providers;

use Illuminate\Support\ServiceProvider;
use Pace\PaceClient;

class PaceServiceProvider extends ServiceProvider {
    public function register(): void {
        $this->mergeConfigFrom(__DIR__ . '/../config/pace.php', 'pace');

        $this->app->singleton(PaceClient::class, function ($app) {
            return new PaceClient(
                apiKey: config('pace.api_key'),
                endpoint: config('pace.endpoint'),
                timeout: config('pace.timeout', 3),
                defaultMetadata: [
                    'environment'       => config('app.env'),
                    'framework'         => 'laravel',
                    'framework_version' => $this->app->version()
                ]
            );
        });
    }

    public function boot(): void {
        if ($this->app->runningInConsole()) {
            $this->publishes([
                __DIR__ . '/../config/pace.php' => config_path('pace.php'),
            ], 'pace-config');
        }
    }
}
