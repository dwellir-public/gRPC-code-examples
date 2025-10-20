package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"
	"google.golang.org/grpc/metadata"

	pb "github.com/dwellir/grpc-code-examples/go/internal/api"
	"github.com/joho/godotenv"
)

// BlockFills represents the structure of block fills
type BlockFills struct {
	Height int64       `json:"height"`
	Time   int64       `json:"time"`
	Fills  []Fill      `json:"fills"`
	Data   interface{} `json:"-"` // For additional fields
}

// Fill represents a single fill
type Fill struct {
	Symbol string  `json:"symbol"`
	Side   string  `json:"side"`
	Price  string  `json:"price"`
	Size   string  `json:"size"`
	Hash   string  `json:"hash"`
}

func main() {
	// Load environment variables
	if err := godotenv.Load(); err != nil {
		log.Println("Warning: .env file not found")
	}

	endpoint := os.Getenv("HYPERLIQUID_ENDPOINT")
	apiKey := os.Getenv("API_KEY")

	if endpoint == "" {
		log.Fatal("Error: HYPERLIQUID_ENDPOINT environment variable is required.\n" +
			"Please create a .env file from .env.example and set your endpoint.")
	}

	// API key is optional - some endpoints are public and don't require authentication
	if apiKey == "" {
		fmt.Println("ℹ️  No API key provided - connecting to public endpoint")
	}

	fmt.Println("🚀 Hyperliquid Go gRPC Client - Stream Block Fills")
	fmt.Println("===================================================")
	fmt.Printf("📡 Endpoint: %s\n\n", endpoint)

	// Create TLS credentials
	creds := credentials.NewTLS(nil)

	// Set up connection options
	opts := []grpc.DialOption{
		grpc.WithTransportCredentials(creds),
		grpc.WithDefaultCallOptions(
			grpc.MaxCallRecvMsgSize(150 * 1024 * 1024), // 150MB
		),
	}

	fmt.Println("🔌 Connecting to gRPC server...")
	conn, err := grpc.Dial(endpoint, opts...)
	if err != nil {
		log.Fatalf("Failed to connect: %v", err)
	}
	defer conn.Close()

	client := pb.NewHyperLiquidL1GatewayClient(conn)
	fmt.Println("✅ Connected successfully!\n")

	// Create context with metadata (API key) only if provided
	ctx := context.Background()
	if apiKey != "" {
		ctx = metadata.AppendToOutgoingContext(ctx, "x-api-key", apiKey)
	}

	// Create cancellable context for graceful shutdown
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()

	// Set up signal handling for graceful shutdown
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)

	go func() {
		<-sigChan
		fmt.Println("\n🛑 Stopping stream...")
		cancel()
	}()

	// Create request - 0 means latest/current block fills
	request := &pb.Timestamp{Timestamp: 0}

	fmt.Println("📥 Starting block fills stream...")
	fmt.Println("Press Ctrl+C to stop streaming\n")

	// Start streaming block fills
	stream, err := client.StreamBlockFills(ctx, request)
	if err != nil {
		log.Fatalf("Failed to start stream: %v", err)
	}

	blockFillsCount := 0

	for {
		response, err := stream.Recv()
		if err == io.EOF {
			break
		}
		if err != nil {
			if ctx.Err() == context.Canceled {
				break
			}
			log.Printf("❌ Stream error: %v", err)
			break
		}

		blockFillsCount++
		fmt.Printf("\n===== BLOCK FILLS #%d =====\n", blockFillsCount)
		fmt.Printf("📦 Response size: %d bytes\n", len(response.Data))

		// Process block fills
		processBlockFills(response.Data, blockFillsCount)

		fmt.Println("\n" + "─────────────────────────────────────────────────")
	}

	fmt.Printf("\n📊 Total block fills received: %d\n", blockFillsCount)
}

func processBlockFills(data []byte, blockFillsNum int) {
	// First unmarshal into a generic map to handle flexible structure
	var rawData map[string]interface{}
	if err := json.Unmarshal(data, &rawData); err != nil {
		// Try as list
		var listData []interface{}
		if err := json.Unmarshal(data, &listData); err != nil {
			log.Printf("❌ Failed to parse JSON: %v", err)
			log.Printf("Raw data (first 200 bytes): %s", data[:min(200, len(data))])
			return
		}
		// Handle list case
		fmt.Printf("💰 BLOCK FILLS #%d DETAILS\n", blockFillsNum)
		fmt.Println("========================")
		fmt.Println("\n📊 Block Fills Summary:")
		fmt.Printf("• Block fills is a list with %d items\n", len(listData))
		if len(listData) > 0 {
			fmt.Printf("• First item type: %T\n", listData[0])
		}
		return
	}

	fmt.Printf("💰 BLOCK FILLS #%d DETAILS\n", blockFillsNum)
	fmt.Println("========================")

	// Display block height if available
	if height, ok := rawData["height"].(float64); ok {
		fmt.Printf("📏 Block Height: %.0f\n", height)
	}

	// Display timestamp
	if timeVal, ok := rawData["time"]; ok {
		var timestamp int64
		switch v := timeVal.(type) {
		case float64:
			timestamp = int64(v)
		case int64:
			timestamp = v
		}

		if timestamp > 0 {
			// Convert from milliseconds to seconds if needed
			if timestamp > 10000000000 { // Likely milliseconds
				timestamp = timestamp / 1000
			}
			t := time.Unix(timestamp, 0)
			fmt.Printf("⏰ Time: %s\n", t.UTC().Format("2006-01-02 15:04:05 UTC"))
		}
	}

	// Display fills data
	if fillsData, ok := rawData["fills"].([]interface{}); ok {
		fmt.Printf("📋 Total Fills: %d\n", len(fillsData))

		// Show first few fill details
		maxFills := min(3, len(fillsData))

		for i := 0; i < maxFills; i++ {
			fillInfo := fmt.Sprintf("  • FILL %d: ", i+1)

			if fillMap, ok := fillsData[i].(map[string]interface{}); ok {
				if symbol, ok := fillMap["symbol"].(string); ok {
					fillInfo += fmt.Sprintf("Symbol: %s", symbol)
				}
				if side, ok := fillMap["side"].(string); ok {
					fillInfo += fmt.Sprintf(", Side: %s", side)
				}
				if price, ok := fillMap["price"].(string); ok {
					fillInfo += fmt.Sprintf(", Price: %s", price)
				} else if price, ok := fillMap["price"].(float64); ok {
					fillInfo += fmt.Sprintf(", Price: %.2f", price)
				}
				if size, ok := fillMap["size"].(string); ok {
					fillInfo += fmt.Sprintf(", Size: %s", size)
				} else if size, ok := fillMap["size"].(float64); ok {
					fillInfo += fmt.Sprintf(", Size: %.2f", size)
				}
				if hash, ok := fillMap["hash"].(string); ok {
					if len(hash) > 12 {
						fillInfo += fmt.Sprintf(", Hash: %s...", hash[:12])
					} else {
						fillInfo += fmt.Sprintf(", Hash: %s", hash)
					}
				}
			} else {
				fillInfo += fmt.Sprintf("%v", fillsData[i])
			}

			fmt.Println(fillInfo)
		}

		if len(fillsData) > maxFills {
			fmt.Printf("  ... and %d more fills\n", len(fillsData)-maxFills)
		}
	}

	// Display any other interesting fields
	fmt.Println("\n📊 Block Fills Summary:")
	for key, value := range rawData {
		if key == "height" || key == "time" || key == "fills" {
			// Already displayed above
			continue
		}

		// Display other fields
		switch v := value.(type) {
		case map[string]interface{}, []interface{}:
			jsonBytes, _ := json.Marshal(v)
			jsonStr := string(jsonBytes)
			if len(jsonStr) > 100 {
				fmt.Printf("• %s: %s...\n", key, jsonStr[:100])
			} else {
				fmt.Printf("• %s: %s\n", key, jsonStr)
			}
		default:
			fmt.Printf("• %s: %v\n", key, value)
		}
	}
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
