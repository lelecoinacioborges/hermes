if ($args.Count -eq 0) {
    docker exec -it hermes hermes
} else {
    docker exec -it hermes hermes @args
}
