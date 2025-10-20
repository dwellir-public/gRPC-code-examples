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

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"
	"google.golang.org/grpc/metadata"

	pb "github.com/dwellir/grpc-code-examples/go/internal/api"
	"github.com/joho/godotenv"
)

// Block represents the structure of a block
type Block struct {
	ABCIBlock struct {
		Proposer             string          `json:"proposer"`
		SignedActionBundles  [][]interface{} `json:"signed_action_bundles"`
	} `json:"abci_block"`
	Resps struct {
		Full [][]interface{} `json:"Full"`
	} `json:"resps"`
}

// ActionTypeCounts tracks different action types
type ActionTypeCounts map[string]int

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

	fmt.Println("🚀 Hyperliquid Go gRPC Client - Stream Blocks")
	fmt.Println("===============================================")
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

	// Create request - 0 means latest/current blocks
	request := &pb.Timestamp{Timestamp: 0}

	fmt.Println("📥 Starting block stream...")
	fmt.Println("Press Ctrl+C to stop streaming\n")

	// Start streaming blocks
	stream, err := client.StreamBlocks(ctx, request)
	if err != nil {
		log.Fatalf("Failed to start stream: %v", err)
	}

	blockCount := 0

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

		blockCount++
		fmt.Printf("\n===== BLOCK #%d =====\n", blockCount)
		fmt.Printf("📦 Response size: %d bytes\n", len(response.Data))

		// Process block
		processBlock(response.Data, blockCount)

		fmt.Println("\n" + "─────────────────────────────────────────────────")
	}

	fmt.Printf("\n📊 Total blocks received: %d\n", blockCount)
}

func processBlock(data []byte, blockNum int) {
	var block Block

	if err := json.Unmarshal(data, &block); err != nil {
		log.Printf("❌ Failed to parse JSON: %v", err)
		log.Printf("Raw data (first 200 bytes): %s", data[:min(200, len(data))])
		return
	}

	fmt.Printf("🧱 BLOCK #%d DETAILS\n", blockNum)
	fmt.Println("===================")

	// Display proposer
	if block.ABCIBlock.Proposer != "" {
		fmt.Printf("👤 Proposer: %s\n", block.ABCIBlock.Proposer)
	}

	// Count action types
	actionTypeCounts := make(ActionTypeCounts)

	for _, actionBundle := range block.ABCIBlock.SignedActionBundles {
		if len(actionBundle) < 2 {
			continue
		}

		bundleData, ok := actionBundle[1].(map[string]interface{})
		if !ok {
			continue
		}

		signedActions, ok := bundleData["signed_actions"].([]interface{})
		if !ok {
			continue
		}

		for _, signedAction := range signedActions {
			signedActionMap, ok := signedAction.(map[string]interface{})
			if !ok {
				continue
			}

			action, ok := signedActionMap["action"].(map[string]interface{})
			if !ok {
				continue
			}

			actionType, ok := action["type"].(string)
			if !ok {
				continue
			}

			// For order type, count the number of orders
			if actionType == "order" {
				if orders, ok := action["orders"].([]interface{}); ok {
					actionTypeCounts[actionType] += len(orders)
				} else {
					actionTypeCounts[actionType]++
				}
			} else {
				actionTypeCounts[actionType]++
			}
		}
	}

	totalActions := 0
	for _, count := range actionTypeCounts {
		totalActions += count
	}

	fmt.Println("📋 Action types:")
	for actionType, count := range actionTypeCounts {
		fmt.Printf("  • %s: %d\n", actionType, count)
	}
	fmt.Printf("  Total actions: %d\n", totalActions)

	// Count order statuses (success vs error)
	successCount := 0
	errorCount := 0

	fullData := block.Resps.Full
	if fullData != nil {
		for _, item := range fullData {
			if len(item) < 2 {
				continue
			}

			entries, ok := item[1].([]interface{})
			if !ok {
				continue
			}

			for _, entry := range entries {
				entryMap, ok := entry.(map[string]interface{})
				if !ok {
					continue
				}

				res, ok := entryMap["res"].(map[string]interface{})
				if !ok {
					continue
				}

				response, ok := res["response"].(map[string]interface{})
				if !ok {
					continue
				}

				if responseType, ok := response["type"].(string); ok && responseType == "order" {
					if data, ok := response["data"].(map[string]interface{}); ok {
						if statuses, ok := data["statuses"].([]interface{}); ok {
							for _, status := range statuses {
								statusMap, ok := status.(map[string]interface{})
								if !ok {
									continue
								}

								if _, hasError := statusMap["error"]; hasError {
									errorCount++
								} else {
									successCount++
								}
							}
						}
					}
				}
			}
		}
	}

	totalStatuses := successCount + errorCount
	fmt.Println("\n📊 Order Statuses:")
	fmt.Printf("  ✅ Success: %d\n", successCount)
	fmt.Printf("  ❌ Error: %d\n", errorCount)
	fmt.Printf("  Total statuses: %d\n", totalStatuses)

	match := totalActions == totalStatuses
	fmt.Printf("\n🔍 Match check: Actions=%d, Statuses=%d, Match=%v\n", totalActions, totalStatuses, match)
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
