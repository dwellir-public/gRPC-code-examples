package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"
	"google.golang.org/grpc/metadata"

	pb "github.com/dwellir/grpc-code-examples/go/internal/api"
	"github.com/joho/godotenv"
)

// OrderBookSnapshot represents the structure of an orderbook snapshot
type OrderBookSnapshot struct {
	Time   interface{}              `json:"time"`
	Levels []map[string]interface{} `json:"levels"`
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

	fmt.Println("🚀 Hyperliquid Go gRPC Client - Get OrderBook Snapshot")
	fmt.Println("=======================================================")
	fmt.Printf("📡 Endpoint: %s\n\n", endpoint)

	// Create TLS credentials
	creds := credentials.NewTLS(nil)

	// Set up connection options with large message support
	// This works with dedicated endpoints that don't have the 64MB limit
	maxSize := 1024 * 1024 * 1024 // 1GB
	opts := []grpc.DialOption{
		grpc.WithTransportCredentials(creds),
		grpc.WithDefaultCallOptions(
			grpc.MaxCallRecvMsgSize(maxSize),
			grpc.MaxCallSendMsgSize(maxSize),
		),
		// Increase HTTP/2 settings for large messages
		grpc.WithInitialWindowSize(1 << 30),          // 1GB
		grpc.WithInitialConnWindowSize(1 << 30),      // 1GB
		grpc.WithReadBufferSize(1024 * 1024 * 64),    // 64MB
		grpc.WithWriteBufferSize(1024 * 1024 * 64),   // 64MB
	}

	fmt.Println("🔌 Connecting to gRPC server...")
	conn, err := grpc.NewClient(endpoint, opts...)
	if err != nil {
		log.Fatalf("Failed to create client: %v", err)
	}
	defer conn.Close()

	client := pb.NewHyperLiquidL1GatewayClient(conn)
	fmt.Println("✅ Connected successfully!\n")

	// Create context
	ctx := context.Background()

	// Add metadata (API key) only if provided
	if apiKey != "" {
		ctx = metadata.AppendToOutgoingContext(ctx, "x-api-key", apiKey)
	}

	// Create request - 0 means current snapshot
	request := &pb.Timestamp{Timestamp: 0}

	fmt.Println("📥 Requesting OrderBook snapshot...")
	fmt.Println("   (This may take a moment for large orderbooks...)\n")

	// Make the gRPC call
	response, err := client.GetOrderBookSnapshot(
		ctx,
		request,
		grpc.MaxCallRecvMsgSize(maxSize),
	)
	if err != nil {
		log.Fatalf("Failed to get orderbook snapshot: %v\n\n"+
			"Note: Some endpoints have message size limits (typically 64MB).\n"+
			"This method works with dedicated endpoints that support larger messages.\n", err)
	}

	fmt.Println("✅ Received OrderBook snapshot!\n")

	// Process the snapshot
	processOrderBookSnapshot(response.Data)
}

func processOrderBookSnapshot(data []byte) {
	// Parse as generic map first to see what keys are available
	var rawData map[string]interface{}
	if err := json.Unmarshal(data, &rawData); err != nil {
		log.Printf("❌ Failed to parse JSON: %v", err)
		if len(data) > 200 {
			log.Printf("Raw data (first 200 bytes): %s", data[:200])
		} else {
			log.Printf("Raw data: %s", data)
		}
		return
	}

	fmt.Println("📊 ORDERBOOK SNAPSHOT")
	fmt.Println("=====================")

	// Display available keys
	fmt.Print("📋 Available data: ")
	keys := make([]string, 0, len(rawData))
	for k := range rawData {
		keys = append(keys, k)
	}
	fmt.Printf("%v\n\n", keys)

	// Display timestamp if available
	if timeVal, ok := rawData["time"]; ok {
		fmt.Printf("⏰ Timestamp: %v\n", timeVal)
	}

	// Display levels info if available
	if levelsVal, ok := rawData["levels"]; ok {
		if levels, ok := levelsVal.([]interface{}); ok {
			fmt.Printf("📈 Total levels: %d\n", len(levels))

			if len(levels) > 0 {
				fmt.Println("\nSample levels (first 3):")
				for i := 0; i < min(3, len(levels)); i++ {
					levelJSON, _ := json.Marshal(levels[i])
					levelStr := string(levelJSON)
					if len(levelStr) > 100 {
						levelStr = levelStr[:100] + "..."
					}
					fmt.Printf("  • Level %d: %s\n", i+1, levelStr)
				}

				if len(levels) > 3 {
					fmt.Printf("  ... and %d more levels\n", len(levels)-3)
				}
			}
		}
	}

	// Display data size info
	dataSizeMB := float64(len(data)) / (1024 * 1024)
	fmt.Printf("\n📦 Response size: %d bytes (%.2f MB)\n", len(data), dataSizeMB)
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
