<?php
declare(strict_types=1);
// Single canonical frontend: GitHub Pages. Keep the PHP API available at
// /ekeberadaansmkbbsul/api.php; redirect only legacy page routes.
header('Cache-Control: no-store');
header('Location: https://kea3123-bit.github.io/ekeberadaansmkbbsul/',true,302);
exit;
