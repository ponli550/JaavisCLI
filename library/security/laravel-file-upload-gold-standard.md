# Laravel Secure File Upload Standard ("Gold Standard")

> **Use Case**: Securely upload files in a "One-Army" ecosystem.
> **Philosophy**: Configuration over Code, Security by Default, Scalable Storage.

---

## 1. The Strategy

1.  **Config-Driven Disks**: Never hardcode `storage_path()` or `public_path()`. Use Laravel's Storage facade so you can switch from Local -> S3 -> DigitalOcean Spaces just by changing `.env`.
2.  **Anti-Enumeration**: Filenames must be random hashes. No `invoice_1.pdf` (guessable).
3.  **MIME-Type Protection**: Trust the *content*, not the *extension*.
4.  **Partitioning**: Store files in date-based folders (`2024/02/`) to prevent directory bloat (OS limits usually hit around 100k files per folder).

---

## 2. The Implementation (`FileHelper.php`)

Place this in `app/Helpers/FileHelper.php`.

```php
<?php

namespace App\Helpers;

use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;

class FileHelper
{
    /**
     * Securely upload a file with automatic path hashing and MIME type enforcement.
     *
     * @param UploadedFile $file
     * @param string $folder e.g., 'avatars', 'proofs'
     * @param string|null $disk 'public', 's3', 'spaces'. Defaults to env config.
     * @return string|null Relative path to the file
     */
    public static function upload(UploadedFile $file, string $folder = 'uploads', ?string $disk = null): ?string
    {
        // 1. Use Configurable Disks
        // Don't hardcode environments. Let .env determine the default disk.
        $disk = $disk ?? config('filesystems.default');

        try {
            // 2. Hash-based Naming
            // Prevents collision and enumeration.
            $filename = Str::random(40);

            // 3. Security: Guess Extension from Content
            // NEVER trust the client's extension ($file->getClientOriginalExtension()).
            // This gets the extension based on the actual MIME type of the file context.
            $extension = $file->hashName(); // Laravel's hashName() generates a hash + safe extension
            // OR if you want to keep your random string:
            $extension = $file->guessExtension();

            $secureName = "{$filename}.{$extension}";

            // 4. Date-Based Partitioning (Scalability)
            // Prevents filesystem limits (e.g., 100k files in one folder freezes some OS UI).
            // Result: uploads/2024/02/random-hash.jpg
            $datePath = date('Y/m');
            $fullPath = "{$folder}/{$datePath}";

            // 5. Store
            // putFileAs automatically handles streaming large files.
            $path = Storage::disk($disk)->putFileAs(
                $fullPath,
                $file,
                $secureName
            );

            return $path;

        } catch (\Throwable $e) {
            // Log the error for the dev, return null for the user
            report($e);
            return null;
        }
    }
}
```

---

## 3. Configuration

### `.env` (Local)
```ini
FILESYSTEM_DISK=public
```

### `.env` (Production)
```ini
FILESYSTEM_DISK=s3
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_DEFAULT_REGION=sgp1
AWS_BUCKET=my-app-bucket
AWS_ENDPOINT=https://sgp1.digitaloceanspaces.com
```

---

## 4. Usage Example

In your Controller:

```php
public function updateAvatar(Request $request)
{
    // 1. Validate (Always First)
    $request->validate([
        'avatar' => ['required', 'image', 'max:5120'], // 5MB
    ]);

    // 2. Upload
    $path = FileHelper::upload($request->file('avatar'), 'avatars');

    if (!$path) {
        return back()->with('error', 'Upload failed. Please try again.');
    }

    // 3. Save to DB
    auth()->user()->update(['avatar_path' => $path]);

    return back()->with('success', 'Avatar updated!');
}
```
