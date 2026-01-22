package com.flightontime.flightapi.service;

import com.flightontime.flightapi.domain.exception.DataScienceApiOfflineException;
import com.flightontime.flightapi.infra.client.datascience.DataScienceClientInterface;
import com.flightontime.flightapi.infra.client.datascience.dto.DataScienceApiRequest;
import com.flightontime.flightapi.infra.client.datascience.dto.DataScienceApiResponse;
import com.flightontime.flightapi.infra.client.datascience.dto.DataScienceResponseDetails;
import io.github.resilience4j.circuitbreaker.CallNotPermittedException;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.client.ResourceAccessException;

import java.time.Instant;
import java.time.temporal.ChronoUnit;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;


@ExtendWith(MockitoExtension.class)
class DataScienceClientServiceTest {

    @Mock
    private DataScienceClientInterface client;

    @InjectMocks
    private DataScienceClientService dataScienceClientService;

    @Test
    void callDataScienceApi_shouldReturnSuccessfulResponse() {
        Instant departureTime = Instant.now().plus(5, ChronoUnit.HOURS);
        DataScienceApiRequest request = new DataScienceApiRequest(
                "GOL",
                "Eduardo Gomes",
                "Congonhas",
                departureTime
        );

        DataScienceApiResponse expectedResponse = new DataScienceApiResponse(
                "Atraso previsto",
                0.85,
                "red",
                new DataScienceResponseDetails(
                        2500.0,
                        15.0,
                        25.0,
                        "Fonte de clima - X"
                )
        );

        when(client.getFlightPrediction(request)).thenReturn(expectedResponse);

        DataScienceApiResponse actualResponse = dataScienceClientService.callDataScienceApi(request);

        assertNotNull(actualResponse);
        assertEquals("Atraso previsto", actualResponse.previsao());
        assertEquals(0.85, actualResponse.probabilidade());
        assertEquals("red", actualResponse.cor());
        assertNotNull(actualResponse.dados_utilizados());
        assertEquals(2500.0, actualResponse.dados_utilizados().distancia());
        assertEquals(15.0, actualResponse.dados_utilizados().chuva());
        assertEquals(25.0, actualResponse.dados_utilizados().vento());
        assertEquals("Fonte de clima - X", actualResponse.dados_utilizados().fonte_clima());

        verify(client, times(1)).getFlightPrediction(request);
    }

    @Test
    void fallbackCallDataScienceApi_shouldThrowExceptionWhenCircuitBreakerIsOpen() {
        Instant departureTime = Instant.now().plus(2, ChronoUnit.HOURS);
        DataScienceApiRequest request = new DataScienceApiRequest(
                "AZUL",
                "Salvador",
                "Recife",
                departureTime
        );

        CallNotPermittedException circuitOpenException = mock(CallNotPermittedException.class);

        DataScienceApiOfflineException exception = assertThrows(
                DataScienceApiOfflineException.class,
                () -> dataScienceClientService.fallbackCallDataScienceApi(request, circuitOpenException)
        );

        assertEquals("O circuito está aberto. Chamada ao serviço de Data Science interrompida", exception.getMessage());
    }

    @Test
    void fallbackCallDataScienceApi_shouldThrowExceptionForGeneralErrors() {
        Instant departureTime = Instant.now().plus(4, ChronoUnit.HOURS);
        DataScienceApiRequest request = new DataScienceApiRequest(
                "GOL",
                "Brasília",
                "Belo Horizonte",
                departureTime
        );

        ResourceAccessException networkException = new ResourceAccessException("Connection timeout");

        DataScienceApiOfflineException exception = assertThrows(
                DataScienceApiOfflineException.class,
                () -> dataScienceClientService.fallbackCallDataScienceApi(request, networkException)
        );

        assertEquals("O serviço de Data Science está fora do ar", exception.getMessage());
    }

    @Test
    void fallbackCallDataScienceApi_shouldThrowExceptionForRuntimeErrors() {
        Instant departureTime = Instant.now().plus(6, ChronoUnit.HOURS);
        DataScienceApiRequest request = new DataScienceApiRequest(
                "LATAM",
                "Porto Alegre",
                "Curitiba",
                departureTime
        );

        RuntimeException runtimeException = new RuntimeException("Unexpected error");

        DataScienceApiOfflineException exception = assertThrows(
                DataScienceApiOfflineException.class,
                () -> dataScienceClientService.fallbackCallDataScienceApi(request, runtimeException)
        );

        assertEquals("O serviço de Data Science está fora do ar", exception.getMessage());
    }
}