# ComputerStore ERP

ComputerStore ERP is a SaaS-ready modular monolith for computer and electronics businesses. It is designed to provide a cohesive foundation for business operations while keeping domain modules clearly separated within a single deployable application.

## Project Overview

The project is an ERP platform focused on the needs of computer and electronics businesses. Its modular monolith structure supports a clear domain boundary today and a practical path for future growth.

## V1 Scope

## V1 Scope

### Platform
- Tenant/company
- Authentication
- Users
- Roles and permissions
- Basic reporting foundation

### ERP
- Employee management
- Store management
- Godown management
- Supplier management
- Brand management
- Category management
- Product management
- Offer management
- Inventory management
- Inventory movement
- Customer management
- Sales management
- Reporting

Purchasing, purchase orders, goods receiving, advanced payment gateway capabilities, advanced AI capabilities, and service management are deferred to V2.

## Architecture

The system will use a modular monolith architecture: frontend and backend applications are separated, while backend business domains remain organized as modules within one FastAPI application and deployment unit.

## Technology Stack

- React + TypeScript for the frontend
- Python + FastAPI for the backend
- SQLAlchemy for database access and ORM capabilities
- PostgreSQL for persistence

## Development Status

Early development. The project structure and technology direction are established; implementation of the V1 scope is in progress.
