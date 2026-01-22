package com.flightontime.flightapi.service;

import com.flightontime.flightapi.domain.airline.dto.AirlineResponse;
import com.flightontime.flightapi.domain.airport.dto.AirportResponse;
import com.flightontime.flightapi.domain.exception.AirlineNotFoundException;
import com.flightontime.flightapi.domain.exception.AirportNotFoundException;
import com.flightontime.flightapi.domain.exception.DataScienceApiOfflineException;
import com.flightontime.flightapi.domain.flight.dto.FlightPredictionResponse;
import com.flightontime.flightapi.domain.flight.dto.FlightRequest;
import com.flightontime.flightapi.infra.client.datascience.dto.DataScienceApiRequest;
import com.flightontime.flightapi.infra.client.datascience.dto.DataScienceApiResponse;
import com.flightontime.flightapi.infra.client.datascience.dto.DataScienceResponseDetails;
import io.github.resilience4j.circuitbreaker.CallNotPermittedException;
import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Instant;
import java.time.temporal.ChronoUnit;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class FlightPredictionServiceTest {

    @Mock
    private DataScienceClientService dataScienceClientService;

    @Mock
    private AirportService airportService;

    @Mock
    private AirlineService airlineService;

    @InjectMocks
    private FlightPredictionService flightPredictionService;


    @Test
    void predictDelay_shouldPredictDelayWithCompleteDataSuccessfully() {
        Instant departureTime = Instant.now().plus(5, ChronoUnit.HOURS);
        FlightRequest flightRequest = new FlightRequest(
                "GOL", "MAO", "CGH", departureTime
        );

        DataScienceApiResponse apiResponse = new DataScienceApiResponse(
                "Atraso previsto",
                0.75,
                "yellow",
                new DataScienceResponseDetails(
                        3000.0,
                        3.0,
                        10.0,
                        "Fonte de clima - X"
                )
        );

        AirlineResponse airLineResponse = new AirlineResponse("GOL");
        AirportResponse originAirport = new AirportResponse("MAO", "Eduardo Gomes");
        AirportResponse destinationAirport = new AirportResponse("CGH", "Congonhas");

        when(airlineService.getAirlineByName("GOL")).thenReturn(airLineResponse);
        when(airportService.getAirportByIataCode("MAO")).thenReturn(originAirport);
        when(airportService.getAirportByIataCode("CGH")).thenReturn(destinationAirport);
        when(dataScienceClientService.callDataScienceApi(any(DataScienceApiRequest.class))).thenReturn(apiResponse);

        FlightPredictionResponse response = flightPredictionService.predictDelay(flightRequest);

        assertNotNull(response);
        assertEquals(0.75, response.probability());
        assertEquals("Atraso previsto", response.prediction());
        assertEquals("yellow", response.color());

        assertNotNull(response.details());
        assertEquals(3000.0, response.details().distance());
        assertEquals(3.0, response.details().rain());
        assertEquals(10.0, response.details().wind());
        assertEquals("Fonte de clima - X", response.details().weatherSource());

        verify(airlineService, times(1)).getAirlineByName("GOL");
        verify(airportService, times(1)).getAirportByIataCode("MAO");
        verify(airportService, times(1)).getAirportByIataCode("CGH");
        verify(dataScienceClientService, times(1)).callDataScienceApi(any(DataScienceApiRequest.class));
    }

    @Test
    void predictDelay_shouldThrowExceptionWhenAirlineIsInvalid() {
        Instant departureDate = Instant.now().plus(10, ChronoUnit.DAYS);
        FlightRequest flightRequest = new FlightRequest("Aeroporto Inexistente", "CGH", "MAO", departureDate);

        when(airlineService.getAirlineByName(flightRequest.airline()))
                .thenThrow(new AirlineNotFoundException("Companhia aérea não encontrada"));

        AirlineNotFoundException exception = assertThrows(AirlineNotFoundException.class,
                () -> flightPredictionService.predictDelay(flightRequest));

        verify(airlineService, times(1)).getAirlineByName("Aeroporto Inexistente");
        verifyNoInteractions(airportService);
        verifyNoInteractions(dataScienceClientService);

    }

    @Test
    void predictDealy_shouldThrowExceptionWhenOriginAirportIsInvalid() {
        Instant departureDate = Instant.now().plus(120, ChronoUnit.MINUTES);
        FlightRequest flightRequest = new FlightRequest("GOL", "XXX", "MAO", departureDate);
        AirlineResponse airlineResponse = new AirlineResponse("GOL");


        when(airlineService.getAirlineByName("GOL")).thenReturn(airlineResponse);
        when(airportService.getAirportByIataCode(flightRequest.origin())).thenThrow(
                new AirportNotFoundException("Aeroporto não encontrado: " + flightRequest.origin())
        );

        AirportNotFoundException exception = assertThrows(AirportNotFoundException.class,
                () -> flightPredictionService.predictDelay(flightRequest));

        verify(airlineService, times(1)).getAirlineByName("GOL");
        verify(airportService, times(1)).getAirportByIataCode("XXX");
        verify(airportService, never()).getAirportByIataCode("MAO");
        verifyNoInteractions(dataScienceClientService);
    }

    @Test
    void predictDealy_shouldThrowExceptionWhenDestinationAirportIsInvalid() {
        Instant departureDate = Instant.now().plus(120, ChronoUnit.MINUTES);
        FlightRequest flightRequest = new FlightRequest("GOL", "CGH", "XXX", departureDate);
        AirlineResponse airlineResponse = new AirlineResponse("GOL");
        AirportResponse airportOriginResponse = new AirportResponse("CGH", "Congonhas");


        when(airlineService.getAirlineByName("GOL")).thenReturn(airlineResponse);
        when(airportService.getAirportByIataCode("CGH")).thenReturn(airportOriginResponse);
        when(airportService.getAirportByIataCode(flightRequest.destination())).thenThrow(
                new AirportNotFoundException("Aeroporto não encontrado: " + flightRequest.destination())
        );

        AirportNotFoundException exception = assertThrows(AirportNotFoundException.class,
                () -> flightPredictionService.predictDelay(flightRequest));

        verify(airlineService, times(1)).getAirlineByName("GOL");
        verify(airportService, times(1)).getAirportByIataCode("CGH");
        verify(airportService, times(1)).getAirportByIataCode("XXX");
        verifyNoInteractions(dataScienceClientService);
    }

    @Test
    void predictDealy_shouldThrowExceptionWhenDataScienceApiIsOffline() {
        Instant departureTime = Instant.now().plus(5, ChronoUnit.HOURS);
        FlightRequest flightRequest = new FlightRequest(
                "GOL", "CGH", "MAO", departureTime
        );

        AirlineResponse airLineResponse = new AirlineResponse("GOL");
        AirportResponse originAirport = new AirportResponse("CGH", "Congonhas");
        AirportResponse destinationAirport = new AirportResponse("MAO", "Eduardo Gomes");

        when(airlineService.getAirlineByName("GOL")).thenReturn(airLineResponse);
        when(airportService.getAirportByIataCode("CGH")).thenReturn(originAirport);
        when(airportService.getAirportByIataCode("MAO")).thenReturn(destinationAirport);
        when(dataScienceClientService.callDataScienceApi(any(DataScienceApiRequest.class)))
                .thenThrow(new DataScienceApiOfflineException("O serviço de Data Science está fora do ar"));


        DataScienceApiOfflineException exception = assertThrows(DataScienceApiOfflineException.class,
                () -> flightPredictionService.predictDelay(flightRequest));


        verify(airlineService, times(1)).getAirlineByName("GOL");
        verify(airportService, times(1)).getAirportByIataCode("CGH");
        verify(airportService, times(1)).getAirportByIataCode("MAO");
        verify(dataScienceClientService, times(1)).callDataScienceApi(any(DataScienceApiRequest.class));
    }

}