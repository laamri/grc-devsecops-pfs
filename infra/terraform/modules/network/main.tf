# 1. Virtual Private Cloud (VPC)
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name    = "${var.project_name}-vpc"
    Project = var.project_name
  }
}

# 2. Internet Gateway (accès Internet pour les sous-réseaux publics)
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name    = "${var.project_name}-igw"
    Project = var.project_name
  }
}

# 3. Sous-réseaux Publics (ALB & NAT Gateway)
resource "aws_subnet" "public" {
  count                   = length(var.public_subnet_cidrs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name    = "${var.project_name}-public-${var.availability_zones[count.index]}"
    Tier    = "public"
    Project = var.project_name
  }
}

# 4. Sous-réseaux Privés (Cluster microservices cloisonné)
resource "aws_subnet" "private" {
  count             = length(var.private_subnet_cidrs)
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = {
    Name    = "${var.project_name}-private-${var.availability_zones[count.index]}"
    Tier    = "private"
    Project = var.project_name
  }
}

# 5. Elastic IP + NAT Gateway (sortie Internet contrôlée pour les sous-réseaux privés)
resource "aws_eip" "nat" {
  domain     = "vpc"
  depends_on = [aws_internet_gateway.igw]

  tags = {
    Name    = "${var.project_name}-nat-eip"
    Project = var.project_name
  }
}

resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id
  depends_on    = [aws_internet_gateway.igw]

  tags = {
    Name    = "${var.project_name}-nat-gw"
    Project = var.project_name
  }
}

# 6. Tables de routage (Public -> IGW, Privé -> NAT Gateway)
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name    = "${var.project_name}-public-rt"
    Project = var.project_name
  }
}

resource "aws_route_table_association" "public" {
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat.id
  }

  tags = {
    Name    = "${var.project_name}-private-rt"
    Project = var.project_name
  }
}

resource "aws_route_table_association" "private" {
  count          = length(aws_subnet.private)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# 7. Security Group ALB (Point d'entrée public : ports 80 et 443 uniquement)
resource "aws_security_group" "alb" {
  name        = "${var.project_name}-sg-alb"
  description = "Flux entrants HTTP/HTTPS uniquement vers le Load Balancer"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTPS depuis Internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP depuis Internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Trafic sortant vers le cluster"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "${var.project_name}-sg-alb"
    Project = var.project_name
  }
}

# 8. Security Group Cluster (Sous-réseau privé : ports 8001 et 8002 depuis ALB uniquement)
resource "aws_security_group" "cluster" {
  name        = "${var.project_name}-sg-cluster"
  description = "Acces restreint aux microservices auth (8001) et task (8002)"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Auth Service depuis ALB"
    from_port       = 8001
    to_port         = 8001
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    description     = "Task Service depuis ALB"
    from_port       = 8002
    to_port         = 8002
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    description = "Communication interne inter-microservices"
    from_port   = 8001
    to_port     = 8002
    protocol    = "tcp"
    self        = true
  }

  egress {
    description = "Sortie Internet via NAT Gateway (ECR, mises a jour)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "${var.project_name}-sg-cluster"
    Project = var.project_name
  }
}