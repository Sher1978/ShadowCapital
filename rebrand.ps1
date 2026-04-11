$docsDir = "docs"
$replacements = @{
    "трение" = "торможение"
    "Трение" = "Торможение"
    "сопротивление" = "торможение"
    "Сопротивление" = "Торможение"
    "Shadow Friction" = "Shadow Braking"
    "shadow friction" = "shadow braking"
    "Хранитель" = "Система безопасности"
}

Get-ChildItem -Path $docsDir -Include *.md, *.txt -Recurse | ForEach-Object {
    $file = $_
    $content = Get-Content $file.FullName -Raw
    $newContent = $content
    foreach ($old in $replacements.Keys) {
        $newContent = $newContent -replace $old, $replacements[$old]
    }
    if ($newContent -ne $content) {
        $newContent | Set-Content $file.FullName
        Write-Output "Updated: $($file.Name)"
    }
}
