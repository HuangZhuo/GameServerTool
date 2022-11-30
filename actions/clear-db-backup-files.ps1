# 清理数据库备份文件，可以配置到「任务计划程序」中定时执行

# 备份根目录
$BACKUP_ROOT = "D:\Z\GameServerTool\actions\db\"
# 每个子目录保留的备份文件数量
$KEEP_FILE_COUNT = 3
# 日志文件过期天数
$EXPIRE_DAYS = 3

function Clear-Backup {
    param (
        $dbPath
    )
    Write-Host 'Process:'$dbPath
    $fileCount = [System.IO.Directory]::GetFiles($dbPath).Count
    if ($fileCount -le $KEEP_FILE_COUNT) {
        return
    }
    $expireTime = (Get-Date).AddDays(-$EXPIRE_DAYS)
    Get-ChildItem -Path $dbPath | Where-Object {
        $_.PSIsContainer -eq $false -and $_.LastWriteTime -lt $expireTime
    } | Remove-Item -Force
}

# https://stackoverflow.com/questions/22379334/a-parameter-cannot-be-found-that-matches-parameter-name-directory
# Get-ChildItem -Path $BACKUP_ROOT -Directory | ForEach-Object { Clear-Backup(Join-Path  $BACKUP_ROOT $_) }
Clear-Backup $BACKUP_ROOT
Get-ChildItem -Path $BACKUP_ROOT | Where-Object { $_.PSIsContainer } | ForEach-Object { Clear-Backup(Join-Path  $BACKUP_ROOT $_) }
