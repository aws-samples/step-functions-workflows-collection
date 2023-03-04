FROM mcr.microsoft.com/dotnet/aspnet:6.0 AS base
WORKDIR /app

FROM mcr.microsoft.com/dotnet/sdk:6.0 AS build
WORKDIR /src
COPY ["WorkflowApp.sln","./"]
COPY ["CopyFilesTask/", "./CopyFilesTask/"]
COPY ["CleanupTask/", "./CleanupTask/"]
COPY ["WorkflowApp.Models/", "./WorkflowApp.Models/"]

WORKDIR /src/CopyFilesTask
RUN dotnet build -c Release -o /app

WORKDIR /src/CleanupTask/
RUN dotnet build -c Release -o /app

FROM build AS publish
RUN dotnet publish -c Release -o /app

FROM base AS final
WORKDIR /app
COPY --from=publish /app .

