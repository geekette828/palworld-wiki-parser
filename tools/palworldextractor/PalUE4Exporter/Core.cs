using System.IO;
using CUE4Parse.Encryption.Aes;
using CUE4Parse.FileProvider;
using CUE4Parse.MappingsProvider.Usmap;
using CUE4Parse.UE4.Assets.Exports.Texture;
using CUE4Parse.UE4.Objects.Core.Misc; // for FGuid
using CUE4Parse.UE4.Versions;
using CUE4Parse_Conversion.Textures;
using Newtonsoft.Json;
using SkiaSharp;
using System.Diagnostics;

namespace PalUE4Exporter;

public record ExportProgress(int Current, int Total, int Failed, string Path, string? OutPath, string? Error);

public record ExportOptions(
    string ArchiveDirectory,
    string MappingsFile,
    string OutputDir,
    string[] PackagePathPrefixes,
    bool DebugOut = false);

public record ExportResult(int Processed, int Failed);

public class AssetExporter
{
    public async Task<ExportResult> RunAsync(
        ExportOptions options,
        IProgress<ExportProgress>? progress = null,
        CancellationToken ct = default)
    {
        var provider = new DefaultFileProvider(
            options.ArchiveDirectory, SearchOption.AllDirectories,
            new VersionContainer(EGame.GAME_UE5_1));
        provider.Initialize();
        provider.MappingsContainer = new FileUsmapTypeMappingsProvider(options.MappingsFile);
        provider.Mount();

        Directory.CreateDirectory(options.OutputDir);

        var jsonSettings = new JsonSerializerSettings { Formatting = Formatting.Indented };

        var matchingFiles = provider.Files
            .Where(kv => options.PackagePathPrefixes.Any(p =>
                    kv.Key.StartsWith(p, StringComparison.OrdinalIgnoreCase))
                && (kv.Key.EndsWith(".uasset") || kv.Key.EndsWith(".umap")))
            .ToList();

        var total = matchingFiles.Count;
        var processed = 0;
        var failed = 0;

        foreach (var (path, file) in matchingFiles)
        {
            ct.ThrowIfCancellationRequested();
            processed++;
            var matchedPrefix = options.PackagePathPrefixes.First(
                p => path.StartsWith(p, StringComparison.OrdinalIgnoreCase));
            string? outPath = null;
            string? error = null;

            try
            {
                var package = provider.LoadPackage(path);
                var exports = package.GetExports().ToArray();

                var subfolder = matchedPrefix.TrimEnd('/').Split('/').Last();
                var relative = path[matchedPrefix.Length..].TrimStart('/');

                foreach (var export in exports)
                {
                    if (export is UTexture2D texture)
                    {
                        var cTexture = texture.Decode(); // CTexture?, not SKBitmap
                        if (cTexture is null)
                        {
                            error = $"Failed to decode texture: {export.Name}";
                            continue;
                        }

                        var imageBytes = TextureEncoder.Encode(cTexture, ETextureFormat.Png, false, out var ext);

                        // texture output path
                        var texOutPath = Path.ChangeExtension(
                            Path.Combine(options.OutputDir, subfolder, relative.Replace('/', Path.DirectorySeparatorChar)),
                            $".{ext}");

                        Directory.CreateDirectory(Path.GetDirectoryName(texOutPath)!);
                        File.WriteAllBytes(texOutPath, imageBytes);

                        outPath = texOutPath;
                    }
                    else
                    {
                        // non-texture JSON export path
                        var fullJson = JsonConvert.SerializeObject(export, jsonSettings);
                        outPath = Path.ChangeExtension(
                            Path.Combine(options.OutputDir, subfolder, relative.Replace('/', Path.DirectorySeparatorChar)),
                            ".json");

                        Directory.CreateDirectory(Path.GetDirectoryName(outPath)!);
                        File.WriteAllText(outPath, fullJson);
                    }
                }
            }
            catch (Exception ex)
            {
                failed++;
                error = ex.Message;
            }

            progress?.Report(new ExportProgress(processed, total, failed, path, outPath, error));
        }


        return new ExportResult(processed, failed);
    }
    //public ExportResult Run(
    //    ExportOptions options,
    //    Action<ExportProgress>? onProgress = null,
    //    CancellationToken ct = default)
    //{
    //    var progress = onProgress is null
    //        ? null
    //        : new Progress<ExportProgress>(onProgress);

    //    return RunAsync(options, progress, ct)
    //        .GetAwaiter()
    //        .GetResult();
    //}

    public ExportResult Run(ExportOptions options)
    {
        return RunAsync(options)
            .GetAwaiter()
            .GetResult();
    }
}