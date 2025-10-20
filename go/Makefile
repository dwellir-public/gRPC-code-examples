.PHONY: all proto deps build clean run-blocks run-fills run-orderbook setup

# Generate protobuf code
proto:
	@echo "Generating protobuf code..."
	@mkdir -p internal/api
	protoc --go_out=internal/api --go_opt=paths=source_relative \
		--go-grpc_out=internal/api --go-grpc_opt=paths=source_relative \
		hyperliquid.proto
	@echo "Protobuf code generated successfully!"

# Install protobuf compiler plugins
install-tools:
	@echo "Installing protobuf compiler plugins..."
	go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
	go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest
	@echo "Tools installed successfully!"

# Download and tidy dependencies
deps:
	@echo "Installing dependencies..."
	go mod tidy
	@echo "Dependencies installed successfully!"

# Setup: install tools, generate proto, and install deps
setup: install-tools proto deps
	@echo ""
	@echo "Setup complete! Don't forget to:"
	@echo "1. Copy .env.example to .env"
	@echo "2. Edit .env with your credentials"
	@echo ""

# Build all examples
build: proto deps
	@echo "Building examples..."
	go build -o stream_blocks stream_blocks.go
	go build -o stream_block_fills stream_block_fills.go
	go build -o get_orderbook_snapshot get_orderbook_snapshot.go
	@echo "Build complete!"

# Run stream_blocks example
run-blocks:
	go run stream_blocks.go

# Run stream_block_fills example
run-fills:
	go run stream_block_fills.go

# Run get_orderbook_snapshot example
run-orderbook:
	go run get_orderbook_snapshot.go

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -f stream_blocks stream_block_fills get_orderbook_snapshot
	rm -f internal/api/*.go
	@echo "Clean complete!"

# Default target
all: build
