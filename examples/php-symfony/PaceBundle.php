<?php

namespace App\PaceBundle;

use Symfony\Component\HttpKernel\Bundle\Bundle;

class PaceBundle extends Bundle {
    public function getPath(): string {
        return \dirname(__DIR__);
    }
}
