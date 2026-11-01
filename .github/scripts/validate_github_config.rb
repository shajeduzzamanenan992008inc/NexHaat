#!/usr/bin/env ruby
# Standard-library-only syntax and policy checks for NexHaat GitHub configuration.
require "yaml"

errors = []
checked = 0

yaml_files = Dir.glob(".github/**/*.{yml,yaml}").sort
yaml_files.each do |path|
  begin
    YAML.parse_file(path)
    checked += 1
  rescue StandardError => e
    errors << "#{path}: YAML parse error: #{e.message}"
  end
end

frontmatter_files = (
  Dir.glob(".github/agents/*.agent.md") +
  Dir.glob(".github/instructions/*.instructions.md") +
  Dir.glob(".github/prompts/*.prompt.md")
).sort

frontmatter_files.each do |path|
  begin
    content = File.read(path, encoding: "UTF-8")
    match = content.match(/\A---\s*\n(.*?)\n---\s*\n/m)
    raise "missing YAML frontmatter" unless match
    YAML.parse(match[1])
    checked += 1
  rescue StandardError => e
    errors << "#{path}: frontmatter error: #{e.message}"
  end
end

workflow_files = Dir.glob(".github/workflows/*.{yml,yaml}")
workflow_files.each do |path|
  content = File.read(path, encoding: "UTF-8")
  errors << "#{path}: mutable action ref @main/@master/@HEAD is forbidden" if
    content.match?(/^\s*uses:\s*[^\s#]+@(main|master|HEAD)(?:\s|$)/i)
  errors << "#{path}: permissions: write-all is forbidden" if
    content.match?(/^\s*permissions:\s*write-all\s*$/i)
  errors << "#{path}: pull_request_target requires a separate security review" if
    content.match?(/^\s*pull_request_target\s*:/)
end

if errors.empty?
  puts "NexHaat GitHub config validation passed (#{checked} YAML/frontmatter files)."
  exit 0
end

warn "NexHaat GitHub config validation failed:"
errors.each { |error| warn " - #{error}" }
exit 1
