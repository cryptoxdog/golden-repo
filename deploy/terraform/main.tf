locals {
  env_lines = file(var.env_file)
  env = tomap({
    for line in split("\n", local.env_lines) :
    trimspace(split("=", line)[0]) => trimspace(join("=", slice(split("=", line), 1, length(split("=", line)))))
    if trimspace(line) != "" && !startswith(trimspace(line), "#") && length(split("=", line)) > 1
  })
}

provider "digitalocean" { token = local.env["DO_API_TOKEN"] }
provider "cloudflare" { api_token = local.env["CLOUDFLARE_API_TOKEN"] }

data "cloudflare_zone" "zone" { filter { name = local.env["CLOUDFLARE_ZONE_NAME"] } }

resource "digitalocean_vpc" "vpc" {
  name = local.env["DO_VPC_NAME"]
  region = local.env["DO_REGION"]
  ip_range = "10.20.0.0/16"
}

resource "digitalocean_ssh_key" "deploy_key" {
  name = local.env["SSH_PUBLIC_KEY_NAME"]
  public_key = local.env["SSH_PUBLIC_KEY"]
}

resource "digitalocean_droplet" "service" {
  name = local.env["SERVICE_NAME"]
  region = local.env["DO_REGION"]
  size = local.env["DO_DROPLET_SIZE"]
  image = local.env["DO_IMAGE"]
  ssh_keys = [digitalocean_ssh_key.deploy_key.fingerprint]
  vpc_uuid = digitalocean_vpc.vpc.id
  backups = lower(local.env["DO_BACKUPS"]) == "true"
  monitoring = lower(local.env["DO_MONITORING"]) == "true"
  user_data = templatefile("${path.module}/cloud-init.yaml.tftpl", {
    service_name = local.env["SERVICE_NAME"]
    container_port = local.env["CONTAINER_PORT"]
  })
}

resource "digitalocean_firewall" "fw" {
  name = "${local.env["SERVICE_NAME"]}-fw"
  droplet_ids = [digitalocean_droplet.service.id]
  inbound_rule { protocol = "tcp" port_range = "22" source_addresses = [local.env["ADMIN_IP_CIDR"]] }
  dynamic "inbound_rule" {
    for_each = lower(local.env["PUBLIC_SERVICE"]) == "true" ? [1] : []
    content { protocol = "tcp" port_range = local.env["HOST_PORT"] source_addresses = ["0.0.0.0/0"] }
  }
  outbound_rule { protocol = "tcp" port_range = "1-65535" destination_addresses = ["0.0.0.0/0"] }
  outbound_rule { protocol = "udp" port_range = "1-65535" destination_addresses = ["0.0.0.0/0"] }
}

resource "cloudflare_record" "service_a" {
  count = local.env["SERVICE_DOMAIN"] != "" ? 1 : 0
  zone_id = data.cloudflare_zone.zone.id
  name = local.env["DNS_RECORD_NAME"]
  type = "A"
  content = digitalocean_droplet.service.ipv4_address
  ttl = tonumber(local.env["DNS_TTL"])
  proxied = lower(local.env["DNS_PROXIED"]) == "true"
}
