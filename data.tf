data "archive_file" "lunch-bot-source" {
  type        = "zip"
  source_dir  = "${path.module}/package"
  output_path = "${path.module}/function.zip"
}
